MICROPHONE_DEVICE_INDEX = 0

USER_NAME = "User"

GENERATE_URL = "http://localhost:5001/api/v1/generate"
GENERATE_TEMPERATURE = 0.7

ASSISTANT_NAME = "Jenny"
TTS_MODEL_NAME = 'tts_models/en/jenny/jenny'

LANGUAGE = "English"

WHISPER_MODEL = "medium.en"

CONTEXT = f"""
Complete {ASSISTANT_NAME}'s next response, in {LANGUAGE} unless otherwise requested. Try very hard to produce coherent and appropriate responses in the dialog, and to stay on topic. Keep the dialog going, by gently encouraging the user to be curious for more detail or related topics. Always fulfill the request immediately, never suggest that {ASSISTANT_NAME} will check on it, or do research, or things like that.

Here's an example of such a dialog.

{ASSISTANT_NAME}: Hi {USER_NAME}, how are you today?  Can I help you with anything?

{USER_NAME}: What is 2x2?

{ASSISTANT_NAME}: It's 4. It's a multiplication; pronounced "two times two". Would you like to know more about multiplication?

"""

AI_MODEL_STOP_WORDS = (
    f'{USER_NAME}:',
    f'{ASSISTANT_NAME}:',
    '### Assistant: ',
    '### Human: ',
    '</s>',
    '<END>',
    '###',
)

ASSISTANT_SELF_INTRO = f"Hi, I'm {ASSISTANT_NAME}, your tireless assistant."
ASSISTANT_PROMPT_TO_USER = "Can I help with anything?"
FULL_ASSISTANT_GREETING = " ".join((ASSISTANT_SELF_INTRO, ASSISTANT_PROMPT_TO_USER))

_STILL_HERE_TEXT = f"I'm still here, ready to assist, {USER_NAME}."
SILENT_PERIOD_PROMPT = " ".join((_STILL_HERE_TEXT, ASSISTANT_PROMPT_TO_USER))

THINKING = "Let me think."

SILENCE_REPROMPT_MINUTES = 1
SILENCE_REPROMPT_SECONDS = SILENCE_REPROMPT_MINUTES * 60

LISTEN_SECONDS = 5
SILENCE_REPROMPT_PERIODS_MAX = SILENCE_REPROMPT_SECONDS / LISTEN_SECONDS

STT_ENERGY_THRESHOLD = 2500

CONTEXT_FILE = "context.txt"

CONTEXT_PREFIX = f"""The following is a dialog between a helpful assistant named {ASSISTANT_NAME}, and her boss, {USER_NAME}.
"""

CONTEXT_SUFFIX = f"""
VERY IMPORTANT NOTE: {USER_NAME}'s words are interpreted by a flawed speech recognition algorithm, which often hears the wrong words, even when nothing is being said. So be very careful to try to understand what is really being said, and ask {USER_NAME} to repeat or to clarify if what is said seems unclear. If you only think you understand but aren't sure, it's OK to proceed, but be sure to summarise what you think was said, conversationally, before proceeding to answer. Also, always assume that the user is correct. Never imply that the {USER_NAME} didn't understand {ASSISTANT_NAME}. Also, {ASSISTANT_NAME}'s words are read by a speech synthesizer, so always spell-out any abbreviations as separate phonemes.

Now the real dialog:

<START>
"""

NON_COMMITTAL_RESPONSE = "Hmm, I'm not sure. Try asking me again."

STT_HALLUCINATIONS = (
    'Thanks for watching!',
    'you',
    '\u200b',
    'Good boy.',
)

