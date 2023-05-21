# Kobold-Assistant

A fully offline voice assistant interface to KoboldAI's large language model API. Can
probably also work online with the KoboldAI horde and online speech-to-text and text-to-speech models, if you really want it to.

It's reasonably good; at least as good as Amazon Alexa, if not better.  It uses the latest coqui "jenny" text to speech model, and openAI's whisper speech recognition, and additionally the model is prompted to know that it's getting text through speech recognition, so is cautious and clarifies if it's not sure what was heard. Unfortunately it has been known to go meta and suggest that you to adjust your microphone! ;)

The assistant is called Jenny by default, per the speech model.

You can tweak the assistant name, speech-to-text model, text-to-speech model, prompts, etc. through configuration, though the config system needs more work to be user-friendly and future-proof.

## Running

- Install as instructed above
- Make sure `koboldcpp` (preferably), `koboldai` or `text-generation-webui` are running,
  with a suitable LLM model loaded, and serving a KoboldAI compatible API at `http://localhost:5001/api/v1/generate` (see Configuration, below, if you need to change this URL).
- Run `kobold-assistant serve` after installing.


## Requirements and Installation

- CUDA (so an nvidia GPU... or an nvidia jetson, I guess) for now (you *might* be able to tweak the settings to run on cpu-only).
- System packages:
	- GCC (c compiler)
	- portaudio development libraries
	- ffmpeg
- KoboldAI, KoboldCPP, or text-generation-webui running locally
  - For now, the only model known to work with this is Alpacino-30b-ggml.  Any Alpaca
    model will PROBABLY work.  I'll add abstractions so that more models work, soon.
- Python >=3.7, <3.11
- pip
- Ubuntu/Debian
- nvidia-cuda-toolkit
- A bunch of other nvidia libraries like cudnn, required by third-party dependencies. for now, just try to run it and install any missing libraries that it complains about per your distro instructions, and failing that, the nvidia instructions for your distro. If your distro isn't supported by nvidia, all bets are off.

I'll try tidy this up in future using docker or something, so you don't have to worry about dependencies, and it "just works", but nvidia make you sign up to their website to get a few of them right now, so there's probably no easy answer at the moment.  Sadly, I don't think this code will get away from any nvidia dependencies for a while.


- download the `*.whl`
- Run `pip install *.whl`.


## Configuration

For now, this is hacky.  I'll improve it soon.

- Install per the instructions above
- run `apt-get install -y $(cat requirements.apt)` (for non-debian/non-ubuntu systems, read requirements.apt, figure out the equivalents for your distro, and ideally submit a PR with a similar requirements file and updated README.md for your distro).
- run `python -c 'import kobold_assistant.default_settings as ds; print(ds.__file__)'`.  Create a new `custom_settings.py` file in the same folder as `default_settings.py`, as follows:

```
from .default_settings import *

SOME_SETTING = new_value
```

where `SOME_SETTING` is one of the variables already present in `default_settings.py`
and `new_value` is some new value that you want to use instead.

**NOTE:** Some values depend on others.  for now, you need to copy any dependent variables that come after the variable that you're modifying into your file, so that they use the custom setting.  Again, this is hacky, and I'll clean it up soon.


## Building (for developers)

- Install poetry per instructions
- Install and make default (via pyenv or whatever) python 3.9.16
- Run the following:

```
poetry build
poetry install
```

Now edit the files and `poetry run kobold-assistant serve` to test.


## Author(s)

- Lee Braiden <leebraid@gmail.com>


## Bugs and support

- Submit a ticket!  Just please try to be clear about what the problem is.  See: https://www.mediawiki.org/wiki/How_to_report_a_bug for instance.

## Contributing

Pull requests welcome - don't be shy :)
