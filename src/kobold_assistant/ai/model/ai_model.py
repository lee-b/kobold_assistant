from ..params import AIParams
from ..prompt import AIPrompt


class AIModelHandler:
    def get_name(self) -> str:
        raise NotImplementedError()

    def get_default_params(self) -> AIParams:
        raise NotImplementedError()

    def format_prompt(self, ai_prompt: AIPrompt) -> str:
        raise NotImplementedError()
