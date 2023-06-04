from typing import Any, Dict, List

from ..params import AIParams
from ..model.ai_model import AIModelHandler


class AIClient:
    async def prompt_ai(self, prompt: str, params: AIParams) -> str:
        raise NotImplementedError()

    async def get_model_name(self) -> str:
        raise NotImplementedError()
