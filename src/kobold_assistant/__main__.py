import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

from .settings import build_settings
from .service import build_dialog_engine

from .dialog_history.dialog_history import DialogHistory


logger = logging.getLogger('kobold-assistant')


# TODO: make this non-global
settings = None


async def load_settings(argv):
    global settings # horrible hack for now

    logging.basicConfig(level=logging.INFO)

    settings = build_settings()
    if settings is None:
        logger.fatal("ERROR: couldn't load settings! Exiting.")
        return None, None

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--quiet', action='store_true')

    valid_modes = (
        'serve',
    )
    parser.add_argument('mode', choices=valid_modes)

    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled.")
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    return settings, args


async def serve(settings):
    # TODO: load prior dialog history here
    dialog_history = DialogHistory()

    dialog_service = build_dialog_engine(settings, dialog_history)

    try:
        await dialog_service.run()

    finally:
        # TODO: save dialog history here
        pass


async def async_main():
    settings, args = await load_settings(sys.argv[1:])
    if settings is None:
        return os.EX_CONFIG

    try:
        if args.mode == 'serve':
            await serve(settings)

    except KeyboardInterrupt:
        msg = "Exiting on user request."
        logger.info(msg)

    return os.EX_OK

def main():
    sys.exit(asyncio.run(async_main()))
