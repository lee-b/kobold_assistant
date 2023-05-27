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


from .settings import build_settings


logger = logging.getLogger()


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


def prompt_ai(prompt: str) -> str:
    post_data = {
        'prompt': prompt,
        'temperature': settings.GENERATE_TEMPERATURE,
#        'max_length': settings.MAX_TOKENS,
#        'max_context_length': settings.MAX_CONTEXT_LENGTH,
    }

    post_json = json.dumps(post_data)
    post_json_bytes = post_json.encode('utf8')

    print(f"settings.GENERATE_URL is {settings.GENERATE_URL!r}")
    req = urllib.request.Request(settings.GENERATE_URL, method="POST")
    req.add_header('Content-Type', 'application/json; charset=utf-8')

    try:
        response_obj = urllib.request.urlopen(req, data=post_json_bytes)
        response_charset = response_obj.info().get_param('charset') or 'utf-8'
        json_response = json.loads(response_obj.read().decode(response_charset))

        try:
            return json_response['results'][0]['text']
        except (KeyError, IndexError) as e:
            print("ERROR: KoboldAI API returned an unexpected response format!", file=sys.stderr)
            return None

    except urllib.error.URLError as e:
        print(f"ERROR: the KoboldAI API returned {e!r}!", file=sys.stderr)
        json_response = None

    return json_response


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


def say(tts_engine, text, cache=False, warmup_only=False):
    # horrible global hack for now; will get fixed
    global temp_audio_files

    # TODO: Choose (or obtain from config) the best speaker
    #       in a better way, per tss_engine.
    if tts_engine.speakers is not None and len(tts_engine.speakers) > 0:
        params['speaker'] = tts_engine.speakers[0]

    # TODO: Choose (or obtain from config) the best language in a better
    #       way, based on locale.
    if tts_engine.languages is not None and len(tts_engine.languages) > 0:
        params['language'] = tts_engine.languages[0]

    expanded_text = expand_to_pronounced_word_form(text)

    if text in temp_audio_files:
        audio = temp_audio_files[text]
    else:
        audio_file = NamedTemporaryFile()

        params = {
            "emotion": "Happy",
            "speed": 1.8,
            "text": expanded_text,
            "file_path": audio_file.name,
        }

        tts_done = False
        while not tts_done:
            try:
                wav_audio = tts_engine.tts_to_file(**params)
                tts_done = True
            except BaseException as e:
                err_msg = f"WARNING: TTS model {settings.TTS_MODEL_NAME!r} threw error {e}. Retrying. If this keeps failing, override the TTS_MODEL_NAME setting, and/or file a bug if it's the default setting."
                for out_fp in (sys.stderr, sys.stdout):
                    # TODO: proper logging :D
                    print(err_msg, file=out_fp)
                time.sleep(1) # because the loop doesn't respond to Ctrl-C otherwise

        audio = AudioSegment.from_wav(audio_file.name)

        if cache:
            temp_audio_files[text] = audio

    if not warmup_only:
        play_audio_segment(audio)


def strip_stop_words(response: str) -> Optional[str]:
    for stop_word in settings.AI_MODEL_STOP_WORDS + [r' \u200b']:
        if stop_word in response:
            logger.debug("stop word %r FOUND in %r", stop_word, response)
            response = response.split(stop_word)[0]
        else:
            logger.debug("stop word %r NOT found in %r", stop_word, response)

    stripped_response = response.strip()
    if stripped_response == "":
        stripped_response = None
    
    print(f"stripped response: {stripped_response!r}, for response: {response!r}")
    return stripped_response


def warm_up_stt_engine(stt_engine, source):
    # warm up / initialize the speech-to-text engine
    if source.stream is None:
        print("ERROR: SpeechRecognition/pyaudio microphone failed to initialize. This seems to be a bug in the pyaudio or SpeechRecognition libraries, but check your MICROPHONE_DEVICE_INDEX setting?", file=sys.stderr)

        class DummyStream:
            def close(self):
                pass

        source.stream = DummyStream() # workaround to allow us to exit cleanly despite the ContextManager bug

        return False

    audio = stt_engine.listen(source, 0)
    stt_engine.recognize_whisper(audio, model=settings.WHISPER_MODEL, language=settings.LANGUAGE.lower())

    return True


def warm_up_tts_engine(tts_engine):
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
        say(tts_engine, common_response_to_cache, cache=True, warmup_only=True)


def build_prompt_text(assistant_name: str, assistant_desc: str, chat_log: List[str], max_context_length: int) -> str:
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


def get_assistant_response(tts_engine, context: str, chat_log: List[str], assistant_name: str, assistant_desc: str) -> Tuple[str, bool]:
    conversation_so_far = build_prompt_text(assistant_name, assistant_desc, chat_log, settings.MAX_CONTEXT_LENGTH)

    stripped_response_text = None
    while not stripped_response_text:
        response_text = None
        while True:
            if settings.SLOW_AI_RESPONSES:
                # Try to naturally let the user know that this will take a while
                say(tts_engine, settings.THINKING, cache=True)

            response_text = prompt_ai(conversation_so_far)

            if response_text is None:
                time.sleep(2)
                print("Retrying request to KoboldAI API", file=sys.stderr)
                continue
            else:
                break

        remapped_text = response_text
        for remap_key, remap_val in settings.AI_TEXT_TO_SPEECH_REMAPPINGS.items():
            remapped_text = remapped_text.replace(remap_key, remap_val)

        stripped_response_text = strip_stop_words(remapped_text)

        # TODO: Handle bad responses by looping with varying
        #       seeds/temperatures until we get a proper response.
        #
        #       For now, we just return a canned non-commital response
        #       instead
        if stripped_response_text is None:
            stripped_response_text = settings.NON_COMMITTAL_RESPONSE
            return stripped_response_text, True
        else:
            return stripped_response_text, False


def get_user_input(tts_engine, stt_engine, source) -> Optional[str]:
    recognize = lambda audio: stt_engine.recognize_whisper(audio, model=settings.WHISPER_MODEL)

    silent_periods_count = 0

    while True:
        if silent_periods_count > settings.SILENCE_REPROMPT_PERIODS_MAX:
            say(tts_engine, settings.SILENT_PERIOD_PROMPT, cache=True)
            silent_periods_count = 0

        # Get user input
        try:
            sys.stdout.flush()

            audio = stt_engine.listen(source, timeout=settings.LISTEN_SECONDS)

            user_response = recognize(audio)

            if len(user_response) == 0:
                silent_periods_count += 1
                continue

            stripped_user_response = user_response.strip()
            if not stripped_user_response:
                silent_periods_count += 1
                continue

            for stt_hallucination in [ settings.STT_HALLUCINATIONS ]:
                if stripped_user_response == stt_hallucination:
                    # debugging
                    print(f"Detected speech-to-text hallucination: {stripped_user_response!r}")
                    silent_periods_count += 1

                    # hacky approach to a labeled continue
                    return None
                else:
                    # debugging
                    print(f"No match for {stripped_user_response!r} as a speech-to-text hallucination against {stt_hallucination!r}")

            # got a valid user response at this point
            silent_periods_count = 0
            return stripped_user_response

        except stt.exceptions.WaitTimeoutError:
            silent_periods_count += 1


def get_user_response(tts_engine, stt_engine, source):
    """handler user input & input validation/retry loop"""

    # hacky factored-out loop to handle python's lack of labeled-continue.
    user_input = None
    while not user_input:
        user_input = get_user_input(tts_engine, stt_engine, source)

    return user_input


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


def serve():
    sleeping = False

    context = "\n".join((settings.CONTEXT_PREFIX, settings.CONTEXT, settings.CONTEXT_SUFFIX))

    tts_engine = TTS(settings.TTS_MODEL_NAME)

    # set up microphone and speech recognition
    stt_engine = stt.Recognizer()
    stt_engine.energy_threshold = settings.STT_ENERGY_THRESHOLD

    mic_device_index = get_microphone_device_id(stt.Microphone)
    mic = stt.Microphone(device_index=mic_device_index)

    if mic is None:
        print("ERROR: couldn't find a working microphone on this system! Connect/enable one, or set MICROPHONE_DEVICE_INDEX in the settings to force its selection.", file=sys.stderr)
        return 1 # error exit code

    chat_log = []

    with mic as source:
        if settings.AUTO_CALIBRATE_MIC is True:
            print(f"Calibrating microphone; please wait {settings.AUTO_CALIBRATE_MIC_SECONDS} seconds (warning: this doesn't seem to work, and might result in the AI not hearing your speech!) ...")
            stt_engine.adjust_for_ambient_noise(source, duration=settings.AUTO_CALIBRATE_MIC_SECONDS)
            print(f"Calibration complete.")

        print("Initializing models and caching some data. Please wait, it could take a few minutes.")

        if not warm_up_stt_engine(stt_engine, source):
            print("ERROR: couldn't initialise the speech-to-text engine! Check previous error messages.", file=sys.stderr)
            return 1 # error exit code

        warm_up_tts_engine(tts_engine)

        initial_log_line = f"{settings.ASSISTANT_NAME}: {settings.FULL_ASSISTANT_GREETING}"
        print(initial_log_line)
        chat_log.append(initial_log_line)

        print("Ready to go.")

        say(tts_engine, settings.FULL_ASSISTANT_GREETING)

        # main dialog loop
        while True:
            print(f"{settings.USER_NAME}: ", end="")
            user_response = get_user_response(tts_engine, stt_engine, source)
            print(user_response)

            user_command = clean_as_user_command(user_response)
            if user_command == settings.SLEEP_COMMAND.lower():
                sleeping = True
                say(tts_engine, settings.GOING_TO_SLEEP, cache=True)
                continue

            elif sleeping and user_command == settings.WAKE_COMMAND.lower():
                sleeping = False
                say(tts_engine, settings.WAKING_UP, cache=True)
                continue

            elif sleeping:
                logging.warning("In sleep mode. Ignoring user input %r. Wake the assistant with %r", user_response, settings.WAKE_COMMAND)
                continue

            user_response_log_line = f'{settings.USER_NAME}: {user_response}'
            chat_log.append(user_response_log_line)

            assistant_response, cached_response = get_assistant_response(tts_engine, context, chat_log, settings.ASSISTANT_NAME, settings.ASSISTANT_DESC)
            log_line = f'{settings.ASSISTANT_NAME}: {assistant_response}'
            print(log_line)
            chat_log.append(log_line)

            say(tts_engine, assistant_response, cache=cached_response)

    return 0


def main():
    global settings # horrible hack for now

    logging.basicConfig(level=logging.DEBUG)

    settings = build_settings()
    if settings is None:
        print("ERROR: couldn't load settings! Exiting.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('serve', 'list-mics',))

    args = parser.parse_args()

    if args.mode == 'serve':
        try:
            return serve()
        except KeyboardInterrupt:
            print("Exiting on user request.")

    elif args.mode == "list-mics":
        stt_engine = stt.Recognizer()
        print(f"Using mic_device_index {settings.MICROPHONE_DEVICE_INDEX}, per settings. These are the available microphone devices:\n")
        mic_list = stt.Microphone.list_microphone_names()
        for k, v in enumerate(mic_list):
            print(f"Device {k}: {v}")
    
        print("I think the working microphones are:")
        working_mics = stt.Microphone.list_working_microphones()

        for k, v in working_mics.items():
            print(f"Device {k}: {v}")

