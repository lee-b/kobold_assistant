import asyncio
from tempfile import NamedTemporaryFile
from typing import List, Sequence

from ...ai.client.ai_client import AIClient
from ...ai.model.ai_model import AIModelHandler
from ...ai.prompt import AIPrompt
from ...ai.params import AIParams
from ...ai.memory.memory import AIMemory
from ...ai.tools import AITool
from ...dialog_history.event import DialogEvent
from ...dialog_history.dialog_history import DialogHistory
from ...dialog_history.typed_text_event import TypedTextEvent
from ...dialog_history.spoken_audio_event import SpokenAudioEvent
from ...tts.tts import TTSEngine

from .assistant import Assistant
from ..user.user import User


class LLM_Assistant(Assistant):
    def __init__(self,
        name: str,
        desc: str,
        initial_greeting: str,
        ai_client: AIClient,
        ai_model: AIModelHandler,
        ai_memory: AIMemory,
        tts_engine: TTSEngine,
        available_tools: Sequence[AITool],
    ):
        self._name = name
        self._desc = desc

        self._initial_greeting = initial_greeting

        self._ai_client = ai_client
        self._ai_model = ai_model
        self._ai_memory = ai_memory

        self._tts_engine = tts_engine

        self._available_tools = available_tools

    def _adjust_ai_params(self, ai_params: AIParams) -> AIParams:
        return ai_params

    async def _on_dialog_event(self, event: DialogEvent, history: DialogHistory):
        #
        # TODO: Fully convert this code from before the refactoring.
        #       It might not even be meant to be here! :D
        #
        if isinstance(event, TypedTextEvent) and isinstance(event.participant, User):
            # user is speaking to us as the assistant(s)

            # TODO: It would be helpful to know if we're the only assistant in the
            #       dialog here, as we should always reply in that case.  For now,
            #       let's assume that's the case.

            ai_params = self._ai_model.get_default_params()
            self._ai_params.adjust(ai_params)

            ai_prompt = AIPrompt(
                self._name,
                self._desc,
                event.participant.get_name(),
                history,
                self._tools,
            )

            # Placeholder tool implementation.
            # At the very least, we probably want to sort
            # tools by priority before trying them.
            for tool in self._available_tools:
                ai_prompt = tool.augment_prompt(ai_prompt)

            # placeholder memory implementation
            self._ai_memory.augment_prompt(ai_prompt)

            prompt_text = self._ai_model.format_prompt(ai_prompt)

            ai_response_text = self._ai_client.prompt_ai(prompt_text, ai_params)
            ai_response_wav_file = await self._tts_engine.tts_to_wav_file(ai_response_text)

            speech_event = SpokenAudioEvent(participant=self, text_spoken=ai_response_text, audio_wav_file=ai_response_wav_file, recipients=[event.participant])
            await history.log_event(speech_event)


    async def _run(self, dialog_history):
        with await self._tts_engine.tts_to_wav_file(self._initial_greeting) as wav_file:
            await self._audio_io.send_audio(wav_file)

        while True:
            asyncio.sleep(1)
