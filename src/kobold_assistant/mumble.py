import wave
import tempfile
import threading
import time
import speech_recognition as sr
import pymumble_py3 as pymumble
import pymumble_py3.constants as pymumble_constants
from pymumble_py3.soundqueue import SoundQueue, SoundChunk


class MumbleClient:
    def __init__(self, server, port, username, password, listen_to_users):
        self.mumble = pymumble.Mumble(server, user=username, password=password, port=int(port))
        self.mumble.start()  # start the mumble connection in a new thread
        time.sleep(1)  # wait a bit to give the connection a chance to establish

        # state control events
        self.receive_state = threading.Event()
        self.send_state = threading.Event()
        self.recognizer = sr.Recognizer()

        # Recognized text
        self.recognized_text = ""

        # Setup sound queues only for specified users
        for user_session_id, user in self.mumble.users.items():
            print(f"I see user {user['name']}")

        self.sound_queues = {user['name']: SoundQueue(self.mumble) for user in self.mumble.users.values() if user['name'] in listen_to_users}

        print(f"self.sound_queues.keys() is {self.sound_queues.keys()!r}")

    def start_receive_text(self):
        self.receive_state.set()
        threading.Thread(target=self.receive_text).start()

    def stop_receive_text(self):
        self.receive_state.clear()

    def start_send_audio(self, wav_file):
        self.send_state.set()
        threading.Thread(target=self.send_audio, args=(wav_file,)).start()

    def stop_send_audio(self):
        self.send_state.clear()

    def receive_text(self):
        while self.receive_state.is_set():
            for user_name, sound_queue in self.sound_queues.items():
                matching_users = [ u for u in self.mumble.users.values() if u['name'] == user_name ]
                if len(matching_users) == 0:
                    continue

                user = matching_users[0]

                while sound_queue.is_sound():
                    sound_chunk = sound_queue.get_sound()
                    # If we got a sound chunk
                    if sound_chunk is not None:
                        with tempfile.NamedTemporaryFile(delete=True) as temp_wav:
                            # Write the raw audio data to the temporary wav file
                            wave_writer = wave.open(temp_wav.name, 'wb')
                            wave_writer.setnchannels(1)
                            wave_writer.setsampwidth(2)  # size in bytes
                            wave_writer.setframerate(48000.0)
                            wave_writer.writeframes(sound_chunk.pcm)
                            wave_writer.close()

                            # Feed the audio file to the speech recognizer
                            with sr.AudioFile(temp_wav.name) as source:
                                audio = self.recognizer.record(source)

                            # Add the recognized text to our text
                            recognized_bit = self.recognizer.recognize_whisper(audio, model="medium.en", language="english")
                            self.recognized_text += recognized_bit

    def send_audio(self, wav_file):
        wf = wave.open(wav_file, "rb")
        while self.send_state.is_set():
            data = wf.readframes(1024)
            if not data:
                break
            self.mumble.sound_output.add_sound(data)
        wf.close()

    def get_recognized_text(self):
        return self.recognized_text

    def close(self):
        self.stop_receive_text()
        self.stop_send_audio()
        self.mumble.stop()
