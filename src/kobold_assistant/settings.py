import copy
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger(__name__)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


default_settings_path = Path(__file__).parent / 'default_settings.json'
user_home_settings_path = Path("~").expanduser() / '.config' / 'kobold_assistant' / 'settings.json'

settings_paths = [
    default_settings_path,
    Path("/") / "etc" / 'kobold_assistant' / 'settings.json',
    user_home_settings_path,
    Path('settings.json'),
]


base_setting_names = set((
    'USER_NAME',
    'ASSISTANT_NAME',
    'LANGUAGE',
    'GENERATE_URI',
))


def load_settings_template():
    settings_template = {}
    for settings_path in settings_paths:
        try:
            if settings_path.exists:
                with open(settings_path) as fp:
                    additional_settings = json.load(fp)
                    settings_template.update(additional_settings)
        except FileNotFoundError:
            pass

    return settings_template


def expand_any_template_vars_in(v: Any, settings: Dict[str, Any]) -> Any:
    if isinstance(v, str):
        return v.format(**settings)
    elif isinstance(v, set):
        return { expand_any_template_vars_in(e, settings) for e in v }
    elif isinstance(v, list):
        return [ expand_any_template_vars_in(e, settings) for e in v ]
    elif isinstance(v, tuple):
        return ( expand_any_template_vars_in(e, settings) for e in v )
    elif isinstance(v, dict):
        return { v_k: expand_any_template_vars_in(v_v, settings) for v_k, v_v in v.items() }
    else:
        return v


def build_settings():
    settings_template = load_settings_template()

    settings = { k: v for k, v in settings_template.items() if k in base_setting_names }
    remaining_settings = { k for k in settings_template.keys() if k not in base_setting_names }

    derived_settings = {}

    # try to loop until we have all variables needed to populate template values in the settings.
    while True:
        if len(remaining_settings) == 0:
            break

        made_progress = False

        settings_to_process = copy.copy(remaining_settings)

        for remaining_setting in settings_to_process:
            try:
                v = settings_template[remaining_setting]
                settings[remaining_setting] = expand_any_template_vars_in(v, settings)
                remaining_settings.remove(remaining_setting)
                made_progress = True
            except KeyError:
                pass

        if not made_progress:
            failed_settings = { k: v for k, v in settings_template.items() if k in remaining_settings}
            logger.fatal("cyclic dependencies in settings %r", failed_settings)
            return None

    return AttrDict(**settings)
