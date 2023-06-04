from tempfile import NamedTemporaryFile


class STTEngine:
    async def recognise_audio(self, audio_file: NamedTemporaryFile) -> str:
        raise NotImplementedError()

    async def warm_up(self):
        with self._make_dummy_audio_sample() as audio_file:
            await self.recognise_audio(self, audio_file)
