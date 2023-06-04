import asyncio
import argparse
import logging
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
        logger.error("ERROR: couldn't load settings! Exiting.", file=sys.stderr)
        return 1

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

    try:
        if args.mode == 'serve':
            await serve(settings)

    except KeyboardInterrupt:
        msg = "Exiting on user request."
        logger.info(msg)


def main():
    sys.exit(asyncio.run(async_main()))
