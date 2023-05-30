import argparse
import importlib.util
import io
import json
import logging
import os
import re
import sys
import time
import urllib
import urllib.parse
import urllib.request
import subprocess
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

import gruut
import pyaudio
import speech_recognition as stt
import torch
import torchaudio
from TTS.api import TTS
from pydub import AudioSegment
from pydub.playback import play as play_audio_segment

from .mumble import MumbleClient

from .radio_silence import RadioSilence
from .settings import build_settings


logger = logging.getLogger('kobold-assistant')


# TODO: make this non-global
settings = None

def get_microphone_device_id(Microphone) -> int:
    """
    Returns the users chosen settings.MICROPHONE_DEVICE_INDEX,
    or if that is None, returns the microphone device index
    for the first working microphone, as a best guess
    """
    if settings.MICROPHONE_DEVICE_INDEX is not None:
        return settings.MICROPHONE_DEVICE_INDEX

    working_mics = Microphone.list_working_microphones()
    if working_mics:
        return list(working_mics.keys())[0]

    return None


def prompt_ai(prompt: str, stop_words: List[str]) -> str:
    post_data = {
        'prompt': prompt,
        'temperature': settings.GENERATE_TEMPERATURE,
        'max_length': min(settings.MAX_TOKENS, 512),
        'max_context_length': settings.MAX_CONTEXT_LENGTH,
        'rep_pen': 1.5,
        'stop_sequence': stop_words,
        'frmttriminc': True,
    }

    if settings.ASSISTANT_SOUL_NUMBER:
        post_data['sampler_seed'] = settings.ASSISTANT_SOUL_NUMBER

    post_json = json.dumps(post_data)
    post_json_bytes = post_json.encode('utf8')

    logger.debug("Calling settings.GENERATE_URL %r with request %r", settings.GENERATE_URL, post_json)

    req = urllib.request.Request(settings.GENERATE_URL, method="POST")
    req.add_header('Content-Type', 'application/json; charset=utf-8')

    try:
        response_obj = urllib.request.urlopen(req, data=post_json_bytes)
        response_charset = response_obj.info().get_param('charset') or 'utf-8'
        json_response = json.loads(response_obj.read().decode(response_charset))

        try:
            response_text = json_response['results'][0]['text']
            return response_text
        except (KeyError, IndexError) as e:
            logger.error("KoboldAI API returned an unexpected response format!")
            return None

    except urllib.error.URLError as e:
        logger.error(f"The KoboldAI API returned %r!", e)

    return None

# horrible global hack for now; will get fixed
temp_audio_files = {}


def expand_text(text_match) -> str:
    text = text_match.group(0)
    replacement = ' '.join([ s.text_spoken for s in gruut.sentences(text) ])
    return replacement


def expand_to_pronounced_word_form(text):
    """Detect mathematical formulae and abbreviations, and replace them"""

    component = r"([0-9]|[A-Za-z]+)"
    term = component + r"\." + component
    abbreviation = r"([A-Z](\.|)){2,}"
    expr_pattern = r"(" + term + r"|" + abbreviation + r"|" + r"\=" + r")"

    expanded_text = re.sub(expr_pattern, expand_text, text)

    return expanded_text


def say(mumble_client, tts_engine, text, cache=False, warmup_only=False):
    # horrible global hack for now; will get fixed
    global temp_audio_files

    assert text.strip() != "", "called say() without any text"

    # TODO: Choose (or obtain from config) the best speaker
    #       in a better way, per tss_engine.
    if tts_engine.speakers is not None and len(tts_engine.speakers) > 0:
        params['speaker'] = tts_engine.speakers[0]

    # TODO: Choose (or obtain from config) the best language in a better
    #       way, based on locale.
    if tts_engine.languages is not None and len(tts_engine.languages) > 0:
        params['language'] = tts_engine.languages[0]

    expanded_text = expand_to_pronounced_word_form(text)

    audio_file = NamedTemporaryFile()

    params = {
        "emotion": "Happy",
        "speed": settings.TTS_SPEECH_SPEED,
        "text": expanded_text,
        "file_path": audio_file.name,
    }

    tts_done = False
    while not tts_done:
        try:
            with RadioSilence(stdout=True, stderr=False):
                wav_audio = tts_engine.tts_to_file(**params)
            tts_done = True
        except Exception as e:
            logger.error(
                "WARNING:"
                " TTS model %r threw error %r. Retrying. If this keeps failing,"
                " override the TTS_MODEL_NAME setting, and/or file a bug if it's the"
                " default setting.",
                settings.TTS_MODEL_NAME,
                e,
            )
            time.sleep(1) # because the loop doesn't respond to Ctrl-C otherwise

    if not warmup_only:
        mumble_client.send_audio(audio_file.name)
        time.sleep(0.5) # TODO: wait on completion properly


def strip_stop_words(response: str) -> Optional[str]:
    for stop_word in settings.AI_MODEL_STOP_WORDS:
        if stop_word in response:
            logger.debug("stop word %r FOUND in %r", stop_word, response)
            response = response.split(stop_word)[0]
        else:
            logger.debug("stop word %r NOT found in %r", stop_word, response)

    stripped_response = response.strip()
    if stripped_response == "":
        stripped_response = None
    
    logging.debug("strip_stop_words(%r): returning %r", response, stripped_response)
    return stripped_response


def warm_up_stt_engine(stt_engine, source):
    # warm up / initialize the speech-to-text engine
    if source.stream is None:
        logging.error("SpeechRecognition/pyaudio microphone failed to initialize. This seems to be a bug in the pyaudio or SpeechRecognition libraries, but check your MICROPHONE_DEVICE_INDEX setting?")

        class DummyStream:
            def close(self):
                pass

        source.stream = DummyStream() # workaround to allow us to exit cleanly despite the ContextManager bug

        return False

    audio = stt_engine.listen(source, 0)

    done = False
    while not done:
        try:
            stt_engine.recognize_whisper(audio, model=settings.WHISPER_MODEL, language=settings.LANGUAGE.lower())
            done = True
        except RuntimeError as e:
            # TODO: should try to say something aloud here, for pure voice-only interactivity
            logger.warning("Speech-to-text engine failed to recognise audio, with error %r. Retrying.", e)

    return True


def warm_up_tts_engine(mumble_client, tts_engine):
    # warm up / initialize the text-to-speech engine
    common_responses_to_cache = [
        settings.SILENT_PERIOD_PROMPT,
        settings.NON_COMMITTAL_RESPONSE,
        settings.GOING_TO_SLEEP,
        settings.WAKING_UP,
    ]
    if settings.SLOW_AI_RESPONSES:
        common_responses_to_cache.append(settings.THINKING)

    for common_response_to_cache in common_responses_to_cache:
        say(mumble_client, tts_engine, common_response_to_cache, cache=True, warmup_only=True)


def build_prompt_text(assistant_name: str, assistant_desc: str, chat_log: List[str], max_context_length: int) -> str:
    max_context_length = max_context_length # koboldai's API doesn't allow more, for now.

    context = "" + assistant_desc
    context_len = len(assistant_desc) + len(assistant_name) + len("\n\n:")

    limited_chat_log = []
    chat_log_pos = len(chat_log) - 1
    while context_len <= max_context_length:
        if chat_log_pos < 0:
            break

        remaining_space = max_context_length - context_len

        next_line = chat_log[chat_log_pos][-remaining_space:]
        chat_log_pos -= 1

        limited_chat_log.insert(0, next_line)
        context_len += remaining_space

    prompt = '\n'.join((context, *limited_chat_log, f'{assistant_name}: '))
    return prompt


def clean_ai_response(text: str) -> str:
    return text.replace('\u200b', '')


def get_assistant_response(mumble_client, tts_engine, context: str, chat_log: List[str], assistant_name: str, assistant_desc: str) -> Tuple[str, bool]:
    conversation_so_far = build_prompt_text(assistant_name, assistant_desc, chat_log, settings.MAX_CONTEXT_LENGTH)

    stripped_response_text = None
    while not stripped_response_text:
        response_text = None
        while True:
            if settings.SLOW_AI_RESPONSES:
                # Try to naturally let the user know that this will take a while
                say(mumble_client, tts_engine, settings.THINKING, cache=True)

            response_text = prompt_ai(conversation_so_far, settings.AI_MODEL_STOP_WORDS)

            if response_text is None:
                time.sleep(2)
                logger.warning("Got no (valid) output from the LLM. Retrying request to KoboldAI API.")
                continue
            else:
                break

        stripped_response_text = strip_stop_words(response_text)
        if stripped_response_text is None:
            return settings.NON_COMMITTAL_RESPONSE, True

        cleaned_text = clean_ai_response(stripped_response_text)

        remapped_text = cleaned_text
        for remap_key, remap_val in settings.AI_TEXT_TO_SPEECH_REMAPPINGS.items():
            remapped_text = remapped_text.replace(remap_key, remap_val)

        # TODO: Handle bad responses by looping with varying
        #       seeds/temperatures until we get a proper response.
        #
        #       For now, we just return a canned non-commital response
        #       instead
        if remapped_text is None or remapped_text.strip() == "":
            return settings.NON_COMMITTAL_RESPONSE, True
        else:
            # TODO: eventually we'll move the return out of this loop and imrpvoe the logic to retry generation until it's good
            return remapped_text, False


def get_user_input(mumble_client, tts_engine, stt_engine, source, notify_on_silent_periods=True) -> Optional[str]:
    if notify_on_silent_periods:
        silent_periods_count = 0

    while True:
#        if notify_on_silent_periods and silent_periods_count > (settings.SILENCE_REPROMPT_PERIODS_MAX:
#            say(mumble_client, tts_engine, settings.SILENT_PERIOD_PROMPT, cache=True)
#            silent_periods_count = 0

        # Get user input
        try:
            print("Attempting to get recognized text")
            user_response = mumble_client.get_recognized_text()

            if user_response is None or len(user_response) == 0:
                print(f"user_response: {user_response!r}; looping")
                if notify_on_silent_periods:
                    silent_periods_count += 1
                continue

            stripped_user_response = user_response.strip()
            if not stripped_user_response:
                print(r"stripped_user_response {stripped_user_response!r}; looping")
                if notify_on_silent_periods:
                    silent_periods_count += 1
                continue

            for stt_hallucination in settings.STT_HALLUCINATIONS:
                if stripped_user_response != stt_hallucination:
                    logger.debug(f"No match for %r as a speech-to-text hallucination against %r", stripped_user_response, stt_hallucination)
                    continue
                    
                logger.debug("Detected speech-to-text hallucination: %r", stripped_user_response)

                if notify_on_silent_periods:
                    silent_periods_count += 1

                # hacky approach to a labeled continue: we return to the
                # outer wrapper function, where we try to get input again.
                print("No output after STT hallucination filtering.")
                return None

            # got a valid user response at this point
            if notify_on_silent_periods:
                silent_periods_count = 0

            print(r"stripped_user_response {stripped_user_response!r}; returning")
            return stripped_user_response

        except stt.exceptions.WaitTimeoutError:
            if notify_on_silent_periods:
                silent_periods_count += 1

    assert False, "reached unreachable code!"


def get_user_response(mumble_client, tts_engine, stt_engine, source, notify_on_silent_periods=True):
    """handler user input & input validation/retry loop"""

    # NOTE: this function doesn't appear to do much, but what it does is wrap the
    # inner function and its loop in another loop, so that we can return from the
    # inner function, to iterate the outer loop, kind of like a
    # 'continue :outer_loop_name'

    return get_user_input(mumble_client, tts_engine, stt_engine, source, notify_on_silent_periods=notify_on_silent_periods)


def clean_as_user_command(s: str) -> str:
    """
    Strip user input down to the bare bones words, so that we match direct commands from the user
    as well as possible despite speech-to-text adding punctuation differently, etc.

    In future, we should really ask the LLM if {settings.USER} is telling {settings.ASSISTANT_NAME}
    to go to sleep, for example, but too much compute, for now.  Might need a smaller command
    and control llm model for that, or hotwords in the speech to text model, or both.
    """

    minimal_command_chars = 'abcdefghijklmnopqrstuvwxyz ' # note the space at the end

    return "".join((c for c in s.lower() if c in minimal_command_chars)).strip()


def run_assistant_dialog(settings, stt_engine, tts_engine, source, context, chat_log, mumble_client):
    if settings.AUTO_CALIBRATE_MIC is True:
        logger.info(f"Calibrating microphone; please wait %d seconds (warning: this doesn't seem to work, and might result in the AI not hearing your speech!) ...", settings.AUTO_CALIBRATE_MIC_SECONDS)
        stt_engine.adjust_for_ambient_noise(source, duration=settings.AUTO_CALIBRATE_MIC_SECONDS)
        logger.info(f"Microphone calibration complete.")

    logger.info("Initializing models and caching some data. Please wait, it could take a few minutes.")

    if not warm_up_stt_engine(stt_engine, source):
        logger.error("Couldn't initialise the speech-to-text engine! Check previous error messages.")
        return 1 # error exit code

    warm_up_tts_engine(mumble_client, tts_engine)

    initial_log_line = f"{settings.ASSISTANT_NAME}: {settings.FULL_ASSISTANT_GREETING}"

    print("All systems go.")

    print(f"{settings.ASSISTANT_NAME_COLOR}{initial_log_line}{settings.RESET_COLOR}")
    chat_log.append(initial_log_line)

    say(mumble_client, tts_engine, settings.FULL_ASSISTANT_GREETING)

    sleeping = False

    # main dialog loop
    while True:
        # prompt user visually, though ideally they don't need to
        # look at output; just interact by voice.
        print(f"{settings.USER_NAME_COLOR}{settings.USER_NAME}:{settings.RESET_COLOR} ", end=""); sys.stdout.flush()

        notify_on_silent_periods = not sleeping
        user_response = get_user_response(mumble_client, tts_engine, stt_engine, source, notify_on_silent_periods=notify_on_silent_periods)
        if user_response is None:
            print("No response from user. Looping.")
            continue

        print(f"{settings.USER_NAME_COLOR}{user_response}{settings.RESET_COLOR}")

        user_command = clean_as_user_command(user_response)
        if user_command == settings.SLEEP_COMMAND.lower():
            sleeping = True
            say(mumble_client, tts_engine, settings.GOING_TO_SLEEP, cache=True)
            print(f"[{settings.ASSISTANT_NAME} is now sleeping, say {settings.WAKE_COMMAND} to wake]")
            continue

        elif sleeping and user_command == settings.WAKE_COMMAND.lower():
            sleeping = False
            print(f"[{settings.ASSISTANT_NAME} is now awake, say {settings.SLEEP_COMMAND} to undo]")
            say(mumble_client, tts_engine, settings.WAKING_UP, cache=True)
            continue

        elif sleeping:
            logging.warning("In sleep mode. Ignoring user input %r. Wake the assistant with %r", user_response, settings.WAKE_COMMAND)
            continue

        user_response_log_line = f'{settings.USER_NAME}: {user_response}'
        chat_log.append(user_response_log_line)

        assistant_response, cached_response = get_assistant_response(mumble_client, tts_engine, context, chat_log, settings.ASSISTANT_NAME, settings.ASSISTANT_DESC)
        chat_log.append(f'{settings.ASSISTANT_NAME}: {assistant_response}')
        print(f'{settings.ASSISTANT_NAME_COLOR}{settings.ASSISTANT_NAME}: {assistant_response}{settings.RESET_COLOR}')

        say(mumble_client, tts_engine, assistant_response, cache=cached_response)


def serve(mumble_client):
    context = "\n".join((settings.CONTEXT_PREFIX, settings.CONTEXT, settings.CONTEXT_SUFFIX))

    # set up microphone and speech recognition
    with RadioSilence(stdout=True):
        tts_engine = TTS(settings.TTS_MODEL_NAME)

        stt_engine = stt.Recognizer()
        stt_engine.energy_threshold = settings.STT_ENERGY_THRESHOLD

        mic_device_index = get_microphone_device_id(stt.Microphone)
        mic = stt.Microphone(device_index=mic_device_index)

    if mic is None:
        logger.error("Couldn't find a working microphone on this system! Connect/enable one, or set MICROPHONE_DEVICE_INDEX in the settings to force its selection.")
        return 1 # error exit code

    chat_log = []

    source = None
    with RadioSilence(stdout=True):
        source = mic.__enter__()

    try:
        run_assistant_dialog(settings, stt_engine, tts_engine, source, context, chat_log, mumble_client)

    finally:
        mic.__exit__(None, None, None)

    return 0


def main():
    global settings # horrible hack for now

    logging.basicConfig(level=logging.INFO)

    settings = build_settings()
    if settings is None:
        logger.error("ERROR: couldn't load settings! Exiting.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('mode', choices=('serve', 'list-mics',))

    parser.add_argument('--mumble-server-address', default='192.168.178.47')
    parser.add_argument('--mumble-port', default=64738, type=int)
    parser.add_argument('--mumble-username', default='Jenny')
    parser.add_argument('--mumble-password', default='Jenny')

    c_and_c_users = ['lb', 'lbphone']

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled.")
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('gruut').setLevel(logging.WARNING)

    try:
        if args.mode == 'serve':
            mumble_client = MumbleClient(args.mumble_server_address, args.mumble_port, args.mumble_username, args.mumble_password, c_and_c_users)
            return serve(mumble_client)

        elif args.mode == "list-mics":
            print(f"Using mic_device_index {settings.MICROPHONE_DEVICE_INDEX}, per settings. These are the available microphone devices:\n")

            with RadioSilence():
                stt_engine = stt.Recognizer()
                mic_list = stt.Microphone.list_microphone_names()
                for k, v in enumerate(mic_list):
                    print(f"Device {k}: {v}")

                print("I think the working microphones are:")
                working_mics = stt.Microphone.list_working_microphones()

                for k, v in working_mics.items():
                    print(f"Device {k}: {v}")

    except KeyboardInterrupt:
        msg = "Exiting on user request."
        logger.info(msg)
        print(msg)
