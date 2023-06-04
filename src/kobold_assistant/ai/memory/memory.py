from ..prompt import AIPrompt


class AIMemory:
    def augment_prompt(self, ai_prompt: AIPrompt):
        raise NotImplementedError()
