from typing import Any

from enum import Enum, auto, unique


@unique
class AIParam(Enum):
    """
    AIParam represents the parameters that can be tuned for a language model.
    """

    # Controls the randomness of predictions.
    # Higher values (closer to 1) make the output more random.
    TEMPERATURE = auto()

    # The number of most probable next words that the model will consider.
    TOP_K = auto()

    # A threshold to choose the top tokens for the next word.
    # The model will discard all options having a cumulative probability less than TOP_P.
    TOP_P = auto()

    # The maximum number of tokens that the model will generate.
    MAX_TOKENS_TO_GENERATE = auto()

    # The minimum number of tokens that the model should generate.
    MIN_TOKENS_TO_GENERATE = auto()

    # The maximum length of the context/input used for generation.
    MAX_CONTEXT_LENGTH = auto()

    # A list of words that the model should avoid using.
    STOP_WORDS = auto()

    # A seed value for the random number generator, to make the generation deterministic.
    SEED = auto()

    # A penalty to apply to the log probabilities of tokens based on their frequency.
    FREQUENCY_PENALTY = auto()

    # A penalty to apply based on the length of the generated text.
    LENGTH_PENALTY = auto()

    # A penalty for repeating the same word or phrase.
    REPEAT_PENALTY = auto()

    # A penalty to apply to the log probabilities of tokens based on whether they have already appeared in the text.
    PRESENCE_PENALTY = auto()


class AIParams(dict):
    def __getitem__(self, key: AIParam) -> Any:
        return super().__getitem__(key)

    def __setitem__(self, key: AIParam, value: Any):
        if not isinstance(key, AIParam):
            raise TypeError(f"Key must be an instance of AIParam, not {type(key).__name__}")
        else:
            return super().__setitem__(key, value)

    @classmethod
    def from_defaults(cls) -> 'AIParams':
        return AIParams(
            TEMPERATURE = 0.6,
            TOP_K = 1,
            TOP_P = 1,
            MAX_TOKENS_TO_GENERATE = 250,
            MIN_TOKENS_TO_GENERATE = 2,
            MAX_CONTEXT_LENGTH = 2048,
            STOP_WORDS = [],
            SEED = 1.0,
            FREQUENCY_PENALTY = 1.0,
            LENGTH_PENALTY = 1.0,
            REPEAT_PENALTY = 1.0,
            PRESENCE_PENALTY = 1.0,
        )
