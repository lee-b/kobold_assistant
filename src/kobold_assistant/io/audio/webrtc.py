import asyncio
import aiortc
import tempfile

import numpy as np
from aiortc import MediaStreamTrack, RTCPeerConnection

from .audio_io import AudioIO, WavFileReceiver


class WebRTCAudioIO(AudioIO):
    def __init__(self):
        self.peer_connection = None
        self.media_stream_track = None
        self.mute_remote_audio = False

    async def run(self, audio_received_callback: WavFileReceiver):
        # Create a peer connection
        self.peer_connection = RTCPeerConnection()

        # Create audio track
        self.media_stream_track = AudioStreamTrack(audio_received_callback)

        # Add audio track to the peer connection
        self.peer_connection.addTrack(self.media_stream_track)

        # Create an offer and set it as the local description
        offer = await self.peer_connection.createOffer()
        await self.peer_connection.setLocalDescription(offer)

    def send_audio(self, audio_wavfile):
        if self.peer_connection is not None and self.media_stream_track is not None:
            self.set_mute_remote_audio_source(True)
            self.media_stream_track.process_audio(audio_wavfile)
            self.set_mute_remote_audio_source(False)

    def set_mute_remote_audio_source(self, enabled: bool):
        self.mute_remote_audio = enabled

        if self.media_stream_track is not None:
            self.media_stream_track.set_recording_enabled(not self.mute_remote_audio)


class AudioStreamTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, audio_received_callback):
        super().__init__()
        self.audio_received_callback = audio_received_callback
        self.segment_duration = 5  # Duration of each audio segment in seconds
        self.silence_threshold = -30  # Silence threshold in dB
        self.segment_buffer = []  # Buffer to store audio segments
        self.is_recording = False

    def process_audio(self, audio_wavfile):
        if not self.is_recording:
            return

        audio, sample_rate = self.load_audio(audio_wavfile)

        # Check if audio contains silence
        is_silence = self.detect_silence(audio, sample_rate)

        if is_silence and self.is_recording:
            # If silence is detected and recording is ongoing, end the segment
            self.save_audio_segment()

        if not is_silence and not self.is_recording:
            # If audio is received and recording is not ongoing, start a new segment
            self.start_recording()

        if self.is_recording:
            # If recording is ongoing, append audio to the segment buffer
            self.segment_buffer.append(audio)

    def load_audio(self, audio_wavfile):
        audio, sample_rate = aiortc.audiotrack.load_wave(audio_wavfile)
        return audio, sample_rate

    def detect_silence(self, audio, sample_rate):
        rms = np.sqrt(np.mean(audio ** 2))
        db = 20 * np.log10(rms)
        return db < self.silence_threshold

    def start_recording(self):
        self.is_recording = True
        self.segment_buffer = []

    def save_audio_segment(self):
        if len(self.segment_buffer) > 0:
            audio_segment = np.concatenate(self.segment_buffer)
            # Generate a unique filename for the audio segment
            filename = f"segment_{len(self.segment_buffer)}.wav"
            self.audio_received_callback(audio_segment, filename)

        self.is_recording = False


def _test():
    def audio_received_callback(audio_data, filename):
        print(f"Received audio segment: {filename}")
        # Perform speech-to-text processing on the received audio segment

    async def run_audio():
        audio_io = AudioIO()
        await audio_io.run(audio_received_callback)

        # Generate a sine wave audio file as a NamedTemporaryFile
        duration = 5  # Duration in seconds
        sample_rate = 44100  # Sample rate (Hz)
        frequency = 440  # Frequency of the sine wave (Hz)

        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * frequency * t)

        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio_file:
            sf.write(temp_audio_file.name, audio_data, sample_rate)

            audio_io.send_audio(temp_audio_file.name)

    asyncio.run(run_audio())


if __name__ == "__main__":
    _test()
