from tempfile import NamedTemporaryFile

from .stt import STTEngine
import speech_recognition as stt


class WhisperSTTEngine(STTEngine):
    def __init__(self, model, language, energy):
        self._model = model
        self._language = language
        self._energy = energy

        self._stt_engine = stt.Recognizer()
        self._stt_engine.energy_threshold = self._energy

    async def recognise_audio(self, audio_file: NamedTemporaryFile) -> str:
        # TODO: restore error handling to here

        res = self._stt_engine.recognize_whisper(
            audio_file,
            model=self._model,
            language=self._language,
        )

        return res
