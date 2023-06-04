import wave
import threading
import opuslib
import speech_recognition as sr
from pymumble_py3 import Mumble
from pymumble_py3.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as EVT_TEXT_MSG
from pymumble_py3.constants import PYMUMBLE_CLBK_SOUNDRECEIVED as EVT_SOUND_RECEIVED
from typing import List, Optional
from io import BytesIO
from pydub import AudioSegment
import audioop
import time


class MumbleClient:
    def __init__(self, server, port, username, password, user_list):
        self.mumble = Mumble(server, user=username, password=password, port=port, debug=False)
        self.mumble.callbacks.set_callback(EVT_TEXT_MSG, self.text_received)
        self.mumble.callbacks.set_callback(EVT_SOUND_RECEIVED, self.sound_received)
        self.mumble.set_receive_sound(True)

        self.recognizer = sr.Recognizer()
        self.audio_data = BytesIO()
        self.user_list = user_list

        self.mumble.start()
        self.mumble.is_ready()  # Wait for client is ready

        self.audio_sent_event = threading.Event()
        self.audio_sent_event.clear()

        self.audio_received_event = threading.Event()
        self.audio_received_event.clear()

    def send_audio_thread(self, wav_file: str):
        audio = AudioSegment.from_wav(wav_file)
        audio = audio.set_channels(1)  # Set to mono
        audio = audio.set_frame_rate(48000)  # Set frame rate to 48000 Hz
        audio = audio.set_sample_width(2)  # Set sample width to 2 bytes (16 bits)

        # Convert audio to raw PCM data
        raw_data = audio.raw_data

        # Now, you can send the PCM data in chunks
        for i in range(0, len(raw_data), 960*2):  # 2 bytes per sample
            frames = raw_data[i:i+960*2]
            if not frames:
                break
            if audio.sample_width != 2:
                frames = audioop.lin2lin(frames, audio.sample_width, 2)
            self.mumble.sound_output.add_sound(frames)

        self.audio_sent_event.set()

    def await_send_completion(self):
        if self.send_audio_thread_obj:
            while True:
                if self.audio_sent_event.wait(1):
                    break

            self.send_audio_thread_obj.join()

    def send_audio(self, wav_file: str):
        print("Sending audio")
        self.audio_sent_event.clear()
        self.send_audio_thread_obj = threading.Thread(target=self.send_audio_thread, args=(wav_file,))
        self.send_audio_thread_obj.start()

    def sound_received(self, user, soundchunk):
        # ignore incoming audio while we're sending, to avoid feedback
        if not self.audio_sent_event.is_set():
            print("Ignoring incoming audio while talking")
            return

        if user['name'] in self.user_list:
            self.audio_data.write(soundchunk.pcm)
            print("Recieved and stored audio")

    def text_received(self, message):
        pass  # Handle text messages if needed

    def start_receive_text(self):
        pass

    def stop_receive_text(self):
        pass

    def get_recognized_text(self) -> Optional[str]:
        print("get_recognized_text(): called")

        self.audio_received_event.clear()
        print("get_recognized_text(): listening")
        asyncio.sleep(50)
        print("get_recognized_text(): done listening")

        self.audio_data.seek(0)
        raw_data = self.audio_data.read()

        # Create a wave file in memory
        output = BytesIO()
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            wav_file.writeframes(raw_data)

        output.seek(0)
        with sr.AudioFile(output) as source:
            audio = self.recognizer.record(source)

        self.audio_received_event.clear()

        try:
            recognized = self.recognizer.recognize_whisper(audio, model="medium.en")
            print(f"get_recognized_text(): returning {recognized}")
            return recognized
        except sr.UnknownValueError:
            print(f"get_recognized_text(): returning None")
            return None

    def close(self):
        self.mumble.stop()
