from typing import Awaitable, Callable, Union

from ..participant.assistant.assistant import Assistant
from ..participant.user.user import User


ParticipantSpeechHandler = Callable[
    [
        'DialogEngine',
        Union[User, Assistant],
        str
    ],
    Awaitable[None],
]


class DialogService:
    async def run(self):
        raise NotImplementedError()
