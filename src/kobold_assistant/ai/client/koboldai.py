import json
import logging
import urllib
from typing import List

from .ai_client import AIClient
from ..model.guess import guess_ai_model_from_name


logger = logging.getLogger(__name__)


class KoboldAI_AIClient(AIClient):
    def __init__(self, generate_url):
        self._generate_url = generate_url

    async def get_model_name(self) -> str:
        # TODO
        return 'unknown'

    async def prompt_ai(self, prompt: str, temperature: int, max_length: int, max_context_length: int, stop_words: List[str]) -> str:
        post_data = {
            'prompt': prompt,
            'temperature': temperature,
            'max_length': min(max_length, 512),
            'max_context_length': max_context_length,
            'rep_pen': 1.5,
            'stop_sequence': stop_words,
            'frmttriminc': True,
        }

        post_json = json.dumps(post_data)
        post_json_bytes = post_json.encode('utf8')

        logger.debug("Calling Generate URL %r with request %r", self._generate_url, post_json)

        req = urllib.request.Request(self._generate_url, method="POST")
        req.add_header('Content-Type', 'application/json; charset=utf-8')

        try:
            response_obj = urllib.request.urlopen(req, data=post_json_bytes)
            response_charset = response_obj.info().get_param('charset') or 'utf-8'
            json_response = json.loads(response_obj.read().decode(response_charset))

            try:
                response_text = json_response['results'][0]['text']
                return response_text
            except (KeyError, IndexError) as e:
                logger.error("KoboldAI API returned an unexpected response format!")
                return None

        except urllib.error.URLError as e:
            logger.error(f"The KoboldAI API returned %r!", e)

        return None
