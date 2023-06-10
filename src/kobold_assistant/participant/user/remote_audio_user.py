import time
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from ...io.audio.audio_io import AudioIO
from ...dialog_history.dialog_history import DialogEvent, DialogHistory
from ...dialog_history.typed_text_event import TypedTextEvent
from ...stt.stt import STTEngine
from ...tts.tts import TTSEngine
from ...dialog_history.dialog_history import DialogHistory, DialogEvent
from ...dialog_history.spoken_audio_event import SpokenAudioEvent
from ...dialog_history.typed_text_event import TypedTextEvent

from .user import User


logger = logging.getLogger(__name__)


class RemoteAudioUser(User):
    def __init__(self, name: str, audio_io: AudioIO, stt_engine: STTEngine, tts_engine: TTSEngine):
        self._name = name
        self._audio_io = audio_io
        self._stt_engine = stt_engine
        self._tts_engine = tts_engine

    def get_name(self) -> str:
        return self._name

    async def on_dialog_event(self, event: 'DialogEvent', history: 'DialogHistory'):
        if isinstance(event, SpokenAudioEvent):
            self._audio_io.send_audio(event.audio_wav_file)

        elif isinstance(event, TypedTextEvent):
            text_as_wav_file = self._tts_engine.tts_to_wav_file(f"System text: {event.text_spoken}")
            self._audio_io.send_audio(text_as_wav_file)

        else:
            logger.warning("RemoteAudioUser: don't know how to handle event type %r", event)

    async def _on_audio_received_from_user(self, dialog_history: 'DialogHistory', wav_file: NamedTemporaryFile):
        """
        Received audio from the (actual) user, so convert to text and add it to the dialog
        as a SpokenTextEvent
        """
        spoken_text = self._stt_engine.recognise_audio(wav_file)

        spoken_audio_event = SpokenAudioEvent(participant=self, text_spoken=spoken_text, audio_wav_file=wav_file)
        dialog_history.log_event(spoken_audio_event)

    async def _run(self, dialog_history: DialogHistory):
        await self._audio_io.run(lambda *args, **kwargs: self._on_audio_from_user(dialog_history, *args, **kwargs))
