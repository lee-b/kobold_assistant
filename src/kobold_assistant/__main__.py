import argparse
import importlib.util
import io
import json
import os
import sys
import time
import urllib
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

import pyaudio
import speech_recognition as stt
import torch
import torchaudio
from TTS.api import TTS
from pydub import AudioSegment
from pydub.playback import play as play_audio_segment


from . import default_settings


CUSTOM_CONFIG_PATH = Path(default_settings.__file__).parent / "custom_settings.py"


try:
    from . import custom_settings as settings
except ImportError:
    settings = default_settings


def text_to_phonemes(text: str) -> str:
    # passthrough, since we (try to) get around this by prompting
    # the AI to spell-out any abbreviations instead, for now.
    # (but it doesn't work with the current prompt)
    return text


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

    if text in temp_audio_files:
        audio = temp_audio_files[text]
    else:
        phonemes = text_to_phonemes(text)

        audio_file = NamedTemporaryFile()

        params = {
            "emotion": "Happy",
            "speed": 1.8,
            "text": phonemes,
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
    for stop_word in settings.AI_MODEL_STOP_WORDS:
        if stop_word in response:
            response = response.split(stop_word)[0]

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
    stt_engine.recognize_whisper(audio, model=settings.WHISPER_MODEL)

    return True

def warm_up_tts_engine(tts_engine):
    # warm up / initialize the text-to-speech engine
    common_responses_to_cache = [
        settings.SILENT_PERIOD_PROMPT,
        settings.NON_COMMITTAL_RESPONSE,
    ]
    if settings.SLOW_AI_RESPONSES:
        common_responses_to_cache.append(settings.THINKING)

    for common_response_to_cache in common_responses_to_cache:
        say(tts_engine, common_response_to_cache, cache=True, warmup_only=True)


def get_assistant_response(tts_engine, context: str, chat_log: List[str], assistant_name: str) -> Tuple[str, bool]:
    conversation_so_far = "\n".join((context, *chat_log, f'{assistant_name}: '))

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

        stripped_response_text = strip_stop_words(response_text)

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

            for stt_hallucination in settings.STT_HALLUCINATIONS:
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


def serve():
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

            user_response_log_line = f'{settings.USER_NAME}: {user_response}'
            chat_log.append(user_response_log_line)

            assistant_response, cached_response = get_assistant_response(tts_engine, context, chat_log, settings.ASSISTANT_NAME)
            log_line = f'{settings.ASSISTANT_NAME}: {assistant_response}'
            print(log_line)
            chat_log.append(log_line)

            say(tts_engine, assistant_response, cache=cached_response)

    return 0


def main():
    print(f"Loaded settings from {settings.__file__}")

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

