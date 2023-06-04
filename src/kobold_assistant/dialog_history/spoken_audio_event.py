from dataclasses import dataclass
from tempfile import NamedTemporaryFile

from ..participant.participant import Participant

from .typed_text_event import TypedTextEvent


@dataclass
class SpokenAudioEvent(TypedTextEvent):
    audio_wav_file: NamedTemporaryFile
