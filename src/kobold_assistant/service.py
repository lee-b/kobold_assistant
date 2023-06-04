import argparse
from datetime import datetime
from typing import Sequence, Union

from .ai.client.koboldai import KoboldAI_AIClient
from .ai.model.guess import guess_ai_model_handler_from_name
from .ai.memory.null_memory import NullAIMemory
from .ai.tools import AITool

from .io.audio.webrtc import WebRTCAudioIO
from .tts.tts import TTSEngine
from .tts.coqui import CoquiTTSEngine
from .stt.whisper import WhisperSTTEngine

from .participant.assistant.assistant import Assistant
from .participant.assistant.simple import LLM_Assistant

from .participant.user.user import User
from .participant.user.remote_audio_user import RemoteAudioUser

from .dialog_service.dialog_service import DialogService
from .dialog_service.simple_dialog_service import SimpleDialogService

from .dialog_history.dialog_history import DialogHistory
from .dialog_history.typed_text_event import TypedTextEvent


async def build_assistants(settings, tts_engine: TTSEngine) -> Sequence[Assistant]:
    ai_client = KoboldAI_AIClient(settings.GENERATE_URL)

    ai_model_name = ai_client.get_model_name()
    ai_model = guess_ai_model_handler_from_name(ai_model_name)

    ai_memory = NullAIMemory()

    available_tools : Sequence[AITool] = []

    assistant = LLM_Assistant(
        settings.ASSISTANT_NAME,
        settings.ASSISTANT_DESC,
        settings.ASSISTANT_GREETING,
        ai_client,
        ai_model,
        ai_memory,
        tts_engine,
        available_tools,
    )

    return [assistant]


async def build_users(settings, tts_engine: TTSEngine) -> Sequence[User]:
    user_audio_io = WebRTCAudioIO()
    user_stt_engine = WhisperSTTEngine(settings.STT_WHISPER_MODEL, settings.STT_WHISPER_LANGUAGE)

    user = RemoteAudioUser(
        settings.USER_NAME,
        user_audio_io,
        user_stt_engine,
        tts_engine,
    )

    return [user]


async def build_dialog_engine(settings, dialog_history) -> DialogService:
    tts_engine = CoquiTTSEngine(settings.TTS_COQUI_MOOD, settings.TTS_COQUI_MODEL_NAME, settings.TTS_COQUI_SPEECH_SPEED)

    users = await build_users(settings, tts_engine)
    assistants = await build_assistants(settings, tts_engine)

    dialog_service = DialogService(
        users,
        assistants,
        dialog_history,
    )

    return dialog_service
