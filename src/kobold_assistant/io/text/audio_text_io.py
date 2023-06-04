from ..audio_io.audio_io import AudioIO


class AudioIOTextIO(TextIO):
    def __init__(self, audio_io: AudioIO, tts_engine: TTSEngine, stt_engine: STTEngine):
        self._tts_engine = tts_engine
        self._stt_engine = stt_engine

        self._audio_io.

    async def on_text_received(self, text: str):
        text_spoken = await self._tts_engine.recognise(wav_file)
        await self.dialog_history.log_event(SpokenTextEvent(participant=self, text_spoken=text_spoken))

    async def send_text(self, text: str):
        with NamedTemporaryFile(suffix='.wav') as ai_response_wav:
            self._tts_engine.tts_to_wav_file(event.text_spoken)
            ai_response_wav.file.seek(0)
            self._audio_io.send_audio(ai_response_wav)

    async def run(self):
        self._audio_io.run()
