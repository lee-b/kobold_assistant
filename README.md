# Kobold-Assistant

A fully offline voice assistant interface to KoboldAI's large language model API. Can
probably also work online with the KoboldAI horde and online speech-to-text and text-to-speech models, if you really want it to.

It's reasonably good; at least as good as Amazon Alexa, if not better. It uses the latest coqui "jenny" text to speech model, and openAI's whisper speech recognition, and additionally the model is prompted to know that it's getting text through speech recognition, so is cautious and clarifies if it's not sure what was heard. Unfortunately it has been known to go meta and suggest that you to adjust your microphone! ;)

The assistant is called Jenny by default, per the speech model.

You can tweak the assistant name, speech-to-text model, text-to-speech model, prompts, etc. through configuration, though the config system needs more work to be user-friendly and future-proof.


## Running

- Install as instructed below
- Make sure `koboldcpp` (preferably), `koboldai` or `text-generation-webui` are running, with a suitable LLM model loaded, and serving a KoboldAI compatible API at `http://localhost:5000/api/v1/generate` (see Configuration, below, if you need to change this URL).
- Run one or more of the commands below.  If you get any errors about missing libraries, follow the instructions about that under Installation, below.

### `serve`

- Run `kobold-assistant serve` after installing.
- Give it a while (at least a few minutes) to start up, especially the first time that you run it, as it downloads a few GB of AI models to do the text-to-speech and speech-to-text, and does some time-consuming generation work at startup, to save time later.  It runs much more comfortably once it gets to the main conversational loop.

### `list-mics`

Run `kobold-assistant list-mics` to list available microphones that `kobold-assistant` can use, when listen for the user's instructions. See the Configuration and Troubleshooting sections below, for more details on `list-mics` and related settings.

## Requirements

- System packages:
	- GCC (c compiler)
	- portaudio development libraries
	- ffmpeg
- KoboldAI, KoboldCPP, or text-generation-webui running locally
  - For now, the only model known to work with this is Alpacino-30b-ggml. Any Alpaca model will PROBABLY work. I'll add abstractions so that more models work, soon.
- Python >=3.7, <3.11
- Ubuntu/Debian


## Installation

- On a Debian-like system (such as Debian, Ubuntu, Linux Mint, or Pop), run `apt-get install -y $(cat requirements.apt)`. For other distros, read `requirements.apt`, figure out the equivalents for your distro (search your distro's packages), and ideally submit a PR with a similar `requirements.yourdistro` file and updated `README.md` for your distro.

- On the first run, if you are missing portaudio or a C compiler, or if you have an nvidia CPU, you may find that you need a bunch of other packages or libraries, like nvidia's cudnn. These are required by third-party dependencies. Most are covered by the step above. Aside from that, just try to run it and install any missing libraries that it complains about per your distro instructions, and failing that, the nvidia instructions for your distro. If your distro isn't supported by nvidia, all bets are off -- you might be better running it as CPU-only.

I'll try tidy this up the dependency situation in future, using docker or something, so you don't have to worry about dependencies, and it "just works", but nvidia make you sign up to their website to get a few of them right now, so there's probably no easy answer at the moment. Sadly, I don't think this code will get away from any nvidia dependencies for a while.

- Download the `*.whl` file from the latest release on github (http://github.com/lee-b/kobold_assistant/)
- Run `pip install *.whl`.


## Configuration

For now, this is hacky. I'll improve it soon.

- Install per the instructions above
- run `python -c 'import kobold_assistant.default_settings as ds; print(ds.__file__)'`. Create a new `custom_settings.py` file in the same folder as `default_settings.py`, as follows:

```
from .default_settings import *

SOME_SETTING = new_value
```

where `SOME_SETTING` is one of the variables already present in `default_settings.py`
and `new_value` is some new value that you want to use instead.

**NOTE:** Some values depend on others. For now, you need to copy any dependent variables that come after the variable that you're modifying into your file, so that they use the custom setting. Again, this is hacky, and I'll clean it up soon.

The most important settings are:

```
# The device number of the microphone to listen for instructions on.
# Run `kobold-assistant list-mics` for a list.
# NOTE: the default should auto-detect this for you.
MICROPHONE_DEVICE_INDEX = None

# Automatically determine the microphone volume based
# on ambient noise levels
AUTO_CALIBRATE_MIC = True

# Energy level (mic volume) to use when not auto-calibrating (per above).
# Range is from 0 to 4000, with 1500 being reasonable for a
# well-calibrated mic.
STT_ENERGY_THRESHOLD = 1500

# The server KoboldAI API endpoint for generating text from a prompt using a large language model
GENERATE_URL = "http://localhost:5000/api/v1/generate"
```

## Building (for developers)

- Install poetry per instructions
- Install and make default (via pyenv or whatever) python 3.9.16
- Run the following:

```
poetry build
poetry install
```

Now edit the files and `poetry run kobold-assistant serve` to test.


## Troubleshooting

#### 'ValueError:  [!] Model file not found in the output path'

This is a bug in the TTS library, if you press Ctrl-C while it's download a model because its downloads aren't atomic (it leaves half a download behind, then gets confused). To work around this, run `rm -rf ~/.local/share/TTS`, and it will download anew.

### 'Detected speech-to-text hallucination: ...'

**CHECK the MICROPHONE_DEVICE_INDEX setting. See Configuration, above.**

This happens when the whisper text-to-speech model hallucinates, and kobold-assistant notices. Essentially, it just means that the text-to-speech model misheard you, or only heard noise and made a guess. Check the MICROPHONE\_DEVICE\_INDEX setting (or it may be listening for audio on a device that's not producing any audio!).  Check your microphone settings (such as the microphone volume and noise cancellation options), and generally ensure that your microphone works: that it's not too quiet or too loud, and so on.  OR, just try again: kobold-assistant will try to recover from this and just go on as if you didn't say anything yet.  If this happens every time, though, you have a configuration issue.

There may be other hallucinations (random text detected that you didn't actually say) that whisper generates, that aren't currently detected. If you encounter any others, please file a PR or bug report. However, sometimes it will just mishear what you say; that much is normal. Try to perfect your microphone settings, and enunciate as clearly as you can.


## Bugs and support

- Submit a ticket! Just please try to be clear about what the problem is. See: https://www.mediawiki.org/wiki/How_to_report_a_bug for instance.


## Contributing

Pull requests welcome - don't be shy :)


## Author(s)

- Lee Braiden <leebraid@gmail.com>
