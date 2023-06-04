from dataclasses import dataclass

from ..participant.participant import Participant

from .event import DialogEvent


@dataclass
class TypedTextEvent(DialogEvent):
    participant: Participant
    text_spoken: str
