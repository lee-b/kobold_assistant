from dataclasses import dataclass
from typing import Sequence

from ..model.ai_model import AIModelHandler
from ..params import AIParam, AIParams


@dataclass
class AIPrompt:
    assistant_name: str
    assistant_desc: str
    user_name: str
    chat_log: Sequence[str]
    last_user_input: str
    available_tools: Sequence[str]
