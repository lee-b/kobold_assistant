from ..params import AIParams

from .ai_model import AIModelHandler
from ..prompt import AIPrompt
from ..params import AIParam, AIParams

from ...dialog_history.dialog_history import DialogHistory
from ...dialog_history.event import DialogEvent
from ...dialog_history.typed_text_event import TypedTextEvent


class DefaultAIModel(AIModelHandler):
    """
    This is a weird hybrid of the instruct, User/Assistant, and RP
    approaches, that seems to work in most cases.
    """

    _PROMPT_INTRO = """### Instruction
A never-ending dialog between a curious human user, called {ai_prompt.user_name} and a helpful assistant called {ai_prompt.assistant_name}.

{ai_prompt.assistant_name} is {ai_prompt.assistant_desc}

Complete {ai_prompt.assistant_name}'s next in the two-way dialog, purely and only from {ai_prompt.assistant_name}'s perspective.
"""

    _PROMPT_OUTRO = """
{ai_prompt.user_name}: {ai_prompt.last_user_input}

### Response
{ai_prompt.assistant_name}: """

    def get_default_params(self) -> AIParams:
        return AIParams.from_defaults()

    def _format_historical_event(self, event: DialogEvent) -> str:
        if issubclass(event, TypedTextEvent):
            return f"{event.participant.get_name()}: {event.spoken_text}"

    def format_prompt(self, ai_prompt: AIPrompt, dialog_history: DialogHistory, ai_params: AIParams) -> str:
        prompt_intro = self.__class__._PROMPT_INTRO.format()
        prompt_outro = self.__class__._PROMPT_OUTRO.format()

        history_for_prompt = []

        # TODO: check if we need to count tokens or chars, and/or (attempt to) convert between the two
        char_budget = ai_params[AIParam.MAX_CONTEXT_LENGTH]

        newline_len = len("\n")
        budget_used = len(prompt_intro) + newline_len * 2 + len(prompt_outro)

        # TODO: we drop the oldest entries right now, but should probably allow
        # keeping a few initial entries, and final entries, and dropping content
        # in the middle, maybe even with a <| content redacted |> or [...] or something
        # to let the AI know that something is being missed. Anything other than ellipsis is
        # probably dangerous unless the AI model explicitly supports that marker, though.

        for event in reversed(dialog_history.get_full_event_log()):
            event_str = self._format_historical_event(event)
            event_str_len = len(event_str)

            # +1 is for the newlines that join this entry to the rest
            space_required = event_str_len + newline_len

            if (space_required + budget_used) > char_budget:
                break

            history_for_prompt.insert(0, event_str)
            budget_used += event_str_len + 1

        return "\n".join(prompt_intro, *history_for_prompt, prompt_outro)
