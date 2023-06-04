from tempfile import NamedTemporaryFile

from .tts import TTSEngine

from TTS.api import TTS


__ALL__ = ['CoquiTTSEngine']


class CoquiTTSEngine(TTSEngine):
    def __init__(self, mood, model_name, speed):
        self._mood = mood
        self._model_name = model_name
        self._speed = speed

        self._tts_engine = TTS(model_name)

    async def tts_to_wav_file(self, text: str) -> NamedTemporaryFile:
        audio_file = NamedTemporaryFile(suffix=".wav")

        params = {
            "emotion": self._mood,
            "speed": self._speed,
            "text": text,
            "file_path": audio_file.name,
        }

        # TODO: Choose (or obtain from config) the best speaker
        #       in a better way, per tss_engine.
        if self._tts_engine.speakers is not None and len(self._tts_engine.speakers) > 0:
            params['speaker'] = self._tts_engine.speakers[0]

        # TODO: Choose (or obtain from config) the best language in a better
        #       way, based on locale.
        if self._tts_engine.languages is not None and len(self._tts_engine.languages) > 0:
            params['language'] = self._tts_engine.languages[0]

        wav_audio = self._tts_engine.tts_to_file(**params)
