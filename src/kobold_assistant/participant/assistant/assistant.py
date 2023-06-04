from tempfile import NamedTemporaryFile
from typing import Any, Dict, List

from ...ai.client.ai_client import AIClient
from ...ai.model.ai_model import AIModelHandler
from ...ai.params import AIParam, AIParams
from ...ai.prompt import AIPrompt

from ..participant import Participant


class Assistant(Participant):
    pass
