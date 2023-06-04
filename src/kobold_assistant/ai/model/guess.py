from ..client import AIClient

from .ai_model import AIModelHandler
from .default import DefaultAIModel


async def guess_ai_model_handler_from_name(model_name: str) -> AIModelHandler:
    clean_model_name = model_name.lower().strip()

    # illustrative of the pattern
#    if 'toolpaca' in clean_model_name:
#        return ...
#    elif 'alpaca' in clean_model_name:
#        return ...
#    elif 'llama' in clean_model_name:
#        return ...
#
#   # etc

    # if we reach here, we don't know the model, so we log
    # a warning and return a default model

    logger.warning("Unrecognised AI model %r; using the default AIModelHandler", model_name)

    return DefaultAIModel()
