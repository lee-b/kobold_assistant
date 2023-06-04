from abc import ABC


class AITool(ABC):
    def get_name(self) -> str:
        raise NotImplementedError()

    def augment_prompt(self, prompt: AIPrompt) -> AIPrompt:
        # TODO: Need to think about this method signature a
        #       LOT more; very placeholdery

        raise NotImplementedError()
