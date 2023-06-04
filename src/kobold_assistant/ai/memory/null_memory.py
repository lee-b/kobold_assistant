from ..prompt import AIPrompt
from .memory import AIMemory


class NullAIMemory(AIMemory):
    def augment_prompt(self, ai_prompt: AIPrompt) -> AIPrompt:
        return ai_prompt
