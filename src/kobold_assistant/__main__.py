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

import torch
import torchaudio

import speech_recognition as stt
from TTS.api import TTS
from pydub import AudioSegment
from pydub.playback import play as play_audio_segment


from . import default_settings


CUSTOM_CONFIG_PATH = Path(default_settings.__file__).parent / "custom_settings.py"


try:
    from . import custom_settings as settings
except ImportError:
    settings = default_settings


print(f"Loaded settings from {settings.__file__}")


def text_to_phonemes(text: str) -> str:
    # passthrough, since we (try to) get around this by prompting
    # the AI to spell-out any abbreviations instead, for now.
    # (but it doesn't work with the current prompt)
    return text


def prompt_ai(prompt: str) -> str:
    post_data = json.dumps({
        'prompt': prompt,
        'temperature': settings.GENERATE_TEMPERATURE,
    }).encode('utf8')

    with urllib.request.urlopen(settings.GENERATE_URL, post_data) as f:
        response_json = f.read().decode('utf-8')
        response = json.loads(response_json)['results'][0]['text']

    print(f"The AI returned {response!r}")

    return response


temp_audio_files = {}


def say(tts_engine, text, cache=False, warmup_only=False):
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
                print(err_msg, file=sys.stderr)
                print(err_msg, file=sys.stdout)
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
    audio = stt_engine.listen(source, 0)

    recognize = lambda audio: stt_engine.recognize_whisper(audio, model=settings.WHISPER_MODEL)

    recognize(audio)


def warm_up_tts_engine(tts_engine):
    # warm up / initialize the text-to-speech engine
    common_responses_to_cache = (
        settings.SILENT_PERIOD_PROMPT,
        settings.THINKING,
        settings.NON_COMMITTAL_RESPONSE,
    )

    for common_response_to_cache in common_responses_to_cache:
        say(tts_engine, common_response_to_cache, cache=True, warmup_only=True)


def get_assistant_response(tts_engine, context: str, chat_log: List[str], assistant_name: str) -> Tuple[str, bool]:
    conversation_so_far = "\n".join((context, *chat_log, f'{assistant_name}: '))

    stripped_response_text = None
    while not stripped_response_text:
        # Try to naturally let the user know that this will take a while
        say(tts_engine, settings.THINKING, cache=True)

        response_text = prompt_ai(conversation_so_far)
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
    mic = stt.Microphone(device_index=settings.MICROPHONE_DEVICE_INDEX)

    # configure speech recognition
    stt_engine.energy_threshold = settings.STT_ENERGY_THRESHOLD

    chat_log = []

    with mic as source:
        warm_up_stt_engine(stt_engine, source)
        warm_up_tts_engine(tts_engine)

        initial_log_line = f"{settings.ASSISTANT_NAME}: {settings.FULL_ASSISTANT_GREETING}"
        print(initial_log_line)
        chat_log.append(initial_log_line)
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

