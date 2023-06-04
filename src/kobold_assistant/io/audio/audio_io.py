from tempfile import NamedTemporaryFile
from typing import Callable


WavFileReceiver = Callable[[NamedTemporaryFile], None]


class AudioIO:
    async def run(self, audio_received_callback: WavFileReceiver):
        raise NotImplementedError()

    def send_audio(self, audio_wavfile):
        raise NotImplementedError()

    def set_mute_remote_audio_source(self, enabled: bool):
        raise NotImplementedError()
