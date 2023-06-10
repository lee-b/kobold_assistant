from dataclasses import dataclass
from typing import Sequence

@dataclass
class AIPrompt:
    assistant_name: str
    assistant_desc: str
    user_name: str
    chat_log: Sequence[str]
    last_user_input: str
    available_tools: Sequence[str]
