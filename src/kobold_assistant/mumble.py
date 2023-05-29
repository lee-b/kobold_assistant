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


class MumbleClient:
    def __init__(self, server, port, username, password, listen_to_users):
        self.mumble = Mumble(server, user=username, password=password, port=port, debug=False)
        self.mumble.callbacks.set_callback(EVT_TEXT_MSG, self.text_received)
        self.mumble.callbacks.set_callback(EVT_SOUND_RECEIVED, self.sound_received)
        self.mumble.set_receive_sound(True)

        self.recognizer = sr.Recognizer()
        self.audio_data = BytesIO()
        self.listen_to_users = listen_to_users

        self.mumble.start()
        self.mumble.is_ready()  # Wait for client is ready

        self.send_audio_event = threading.Event()

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

    def start_send_audio(self, wav_file: str):
        self.send_audio_event.clear()
        self.send_audio_thread_obj = threading.Thread(target=self.send_audio_thread, args=(wav_file,))
        self.send_audio_thread_obj.start()

    def stop_send_audio(self):
        self.send_audio_event.set()
        if self.send_audio_thread_obj:
            self.send_audio_thread_obj.join()

    def sound_received(self, user, soundchunk):
        if user['name'] in self.listen_to_users:
            self.audio_data.write(soundchunk.pcm)

    def text_received(self, message):
        pass  # Handle text messages if needed

    def start_receive_text(self):
        self.mumble.channels.find_by_name('Root').send_text_message('Start receiving text')

    def stop_receive_text(self):
        self.mumble.channels.find_by_name('Root').send_text_message('Stop receiving text')

    def get_recognized_text(self) -> Optional[str]:
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
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None

    def close(self):
        self.mumble.stop()

    def send_audio(self, wav_file: str):
        self.start_send_audio(wav_file)

    def receive_text(self):
        self.start_receive_text()
