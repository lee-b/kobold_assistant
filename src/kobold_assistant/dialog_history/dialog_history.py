from dataclasses import dataclass
from typing import Awaitable, Callable, Sequence

from ..participant.participant import Participant
from .event import DialogEvent


DialogEventHandler = Callable[[DialogEvent, 'DialogHistory'], Awaitable[None]]


class DialogHistory:
    def __init__(self):
        self._chat_log : Sequence[DialogEvent] = []
        self._event_handlers = set()

    async def add_event_handler(self, handler):
        self._event_handlers.add(handler)

    async def remove_event_handler(self, handler):
        self._event_handlers.remove(handler)

    def log_event(self, event: DialogEvent):
        self._chat_log.append(event)

        for handler in self._event_handlers:
            handler(event, self)

    def get_full_log(self) -> Sequence[DialogEvent]:
        return self._chat_log

    # TODO: add a more sane get_log_range(from_timestamp, to_timestamp) function
