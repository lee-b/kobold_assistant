from tempfile import NamedTemporaryFile


__ALL__ = ['TTSEngine']


class TTSEngine:
    async def tts_to_wav_file(self, text: str) -> NamedTemporaryFile:
        raise NotImplementedError()

    async def warm_up_tts_engine(self, debug):
        global settings # horrible hack for now

        # warm up / initialize the text-to-speech engine
        common_responses_to_cache = [
            settings.SILENT_PERIOD_PROMPT,
            settings.NON_COMMITTAL_RESPONSE,
            settings.GOING_TO_SLEEP,
            settings.WAKING_UP,
        ]
        if settings.SLOW_AI_RESPONSES:
            common_responses_to_cache.append(settings.THINKING)

        for common_response_to_cache in common_responses_to_cache:
            await self.tts_to_wav_file(
                common_response_to_cache,
                cache=True,
                warmup_only=True,
                debug=debug,
            )
