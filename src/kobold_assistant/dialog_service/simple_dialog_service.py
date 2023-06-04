import asyncio
import logging
import time
from tempfile import NamedTemporaryFile
from typing import AsyncCallable, Dict, Mapping, Sequence, Union

from ..participant.assistant.assistant import Assistant
from ..participant.user.user import User
from ..ai.client.ai_client import AIClient
from ..ai.model.ai_model import AIModelHandler
from ..ai.memory.memory import AIMemory
from ..audio_io.audio_io import AudioIO
from ..stt.stt import STTEngine
from ..tts.tts import TTSEngine
from ..dialog_history.dialog_history import DialogHistory
from ..dialog_history.event import DialogEvent
from ..dialog_history.typed_text_event import TypedTextEvent

from .dialog_service import DialogService, ParticipantSpeechHandler


logger = logging.getLogger(__name__)


class SimpleDialogService(DialogService):
    def __init__(self, users: Sequence[User], assistants: Sequence[Assistant], dialog_history: DialogHistory):
        self._users = users
        self._assistants = assistants
        self._dialog_history = dialog_history

    async def run(self):
        tasks = []

        for user in self._users:
            task = user.run(self._dialog_history)
            tasks.append(task)

        for assistant in self._assistants:
            task = assistant.run(self._dialog_history)
            tasks.append(task)

        await asyncio.gather(tasks)
