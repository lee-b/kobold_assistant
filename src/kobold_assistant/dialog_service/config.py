from dataclasses import dataclass
from typing import Sequence

from ..participant.assistant.assistant import Assistant
from ..participant.user.user import User
from ..dialog_history.dialog_history import DialogHistory


@dataclass
class DialogServiceConfig:
    users: Sequence[User]
    assistants: Sequence[Assistant]
    dialog_history: DialogHistory
