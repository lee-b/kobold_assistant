# Kobold-Assistant

A fully offline voice assistant interface to KoboldAI's large language model API. Can probably also work online with the KoboldAI horde and online speech-to-text and text-to-speech models, if you really want it to.

It's reasonably good; at least as good as Amazon Alexa, if not better. It uses the latest coqui "jenny" text to speech model, and openAI's whisper speech recognition, and additionally the model is prompted to know that it's getting text through speech recognition, so is cautious and clarifies if it's not sure what was heard. Unfortunately it has been known to go meta and suggest that you to adjust your microphone! ;)

The assistant is called Jenny by default, per the speech model.

You can tweak the assistant name, speech-to-text model, text-to-speech model, prompts, etc. through configuration, though the config system needs more work to be user-friendly and future-proof.

## Discord Server

We have a channel on the Kobold-AI server. Please try to file real bugs and requests on github instead, but this is a good place to initially discuss possible bugs, chat about ideas,
etc. https://discord.com/channels/849937185893384223/1110256272403599481

## Running

- Install as instructed below
- Make sure `KoboldAI` (preferably) (a.k.a, `KoboldAI-Client`), `KoboldCPP` or `text-generation-webui` are running, with a suitable LLM model loaded, and serving a KoboldAI compatible API at `http://localhost:5000/api/v1/generate` (see Configuration, below, if you need to change this URL). See KoboldAI below, for a quickstart guide.
- Run one or more of the commands below.  If you get any errors about missing libraries, follow the instructions about that under Installation, below.

### `serve`

- Run `kobold-assistant serve` after installing.
- Give it a while (at least a few minutes) to start up, especially the first time that you run it, as it downloads a few GB of AI models to do the text-to-speech and speech-to-text, and does some time-consuming generation work at startup, to save time later.  It runs much more comfortably once it gets to the main conversational loop.
- While running, the system responds to special control commands.  See Control Commands, below.

### `list-mics`

Run `kobold-assistant list-mics` to list available microphones that `kobold-assistant` can use, when listen for the user's instructions. See the Configuration and Troubleshooting sections below, for more details on `list-mics` and related settings.

## Requirements

- System packages:
	- GCC (c compiler)
	- portaudio development libraries
	- ffmpeg
- KoboldAI, KoboldCPP, or text-generation-webui running locally
  - For now, the only model known to work with this is stable-vicuna-13B-GPTQ. Any Alpaca-like or vicuna model will PROBABLY work. I'll add abstractions so that more models work, soon. Feel free to submit a PR with known-good models, or changes for multiple/other model support.
- Python >=3.7, <3.11
- Ubuntu/Debian

### Control Commands

While running, there are two special commands that kobold-assistant responds to:

#### `settings.SLEEP_COMMAND` (default: 'Sleep Jenny')

This tells the assistant to go to sleep (to stop listening) until a wake command is given (see below).

#### `settings.WAKE_COMMAND` (default: 'Wake up Jenny')

This tells the assistant to start listening again, after it has been told to go to sleep (see above).


## Installation

- On a Debian-like system (such as Debian, Ubuntu, Linux Mint, or Pop), run `apt-get install -y $(cat requirements.apt)`. For other distros, read `requirements.apt`, figure out the equivalents for your distro (search your distro's packages), and ideally submit a PR with a similar `requirements.yourdistro` file and updated `README.md` for your distro.

- On the first run, if you are missing portaudio or a C compiler, or if you have an nvidia CPU, you may find that you need a bunch of other packages or libraries, like nvidia's cudnn. These are required by third-party dependencies. Most are covered by the step above. Aside from that, just try to run it and install any missing libraries that it complains about per your distro instructions, and failing that, the nvidia instructions for your distro. If your distro isn't supported by nvidia, all bets are off -- you might be better running it as CPU-only.

I'll try tidy this up the dependency situation in future, using docker or something, so you don't have to worry about dependencies, and it "just works", but nvidia make you sign up to their website to get a few of them right now, so there's probably no easy answer at the moment. Sadly, I don't think this code will get away from any nvidia dependencies for a while.

- Download the `*.whl` file from the latest release on github (http://github.com/lee-b/kobold_assistant/)
- Run `pip install *.whl`.


## Configuration

To customize the configuration, run `kobold_assistant default-config-path`, and copy the the file at that path to `~/.config/kobold_assistant/settings.json`, then edit it.  You can also place config in `/etc/kobold_assistant/settings.json`.

The most important settings are as follows:

### `GENERATE_URL = "http://localhost:5000/api/v1/generate"`

The KoboldAI API server endpoint, for generating text from a prompt using a large language model.  Check the documentation and terminal output of KoboldAI-Client, KoboldCPP, Text-Generation-WebUI, or whichever other compatible server you're using.

### `MICROPHONE_DEVICE_INDEX: null`

The device number of the microphone to listen for instructions on.
Run `kobold-assistant list-mics` for a list.  null means choose the default.

NOTE: The default (null) "should" auto-detect this for you; see the
      For now, see the SpeechRecognition library docs for details on exactly
      how this works.

### `AUTO_CALIBRATE_MIC: true`

Automatically determine the microphone volume based on ambient noise levels.

### `STT_ENERGY_THRESHOLD: 1500`

Energy level (mic volume) to use when NOT auto-calibrating (per above). Range is from 0 to 4000, with 1500 being reasonable for a
well-calibrated mic.

## KoboldAI

Really, you should check the KoboldAI instructions, but as a quick guide to getting it running on Debian, Ubuntu, Linux Mint, Pop! OS, or similar Debian-based Linux distros, for the purposes of running this, here's how to do it, at *present*. No guarantees that this will continue to work.

### Known-good models

### ROUGH requirements

ROUGH requirements (check the KoboldAI docs for better requirements):
    - nvidia card with CUDA and at least 12GB of Video RAM (VRAM)
    - A recent Debian-based distro
    - A GUI desktop session (this approach needs a browser)

NOTE: this is NOT the official KoboldAI version, but a development branch that supports 4bit quantized models. In future, it should be possible to use the official version instead, after this feature has been merged into it.

### Debian/Ubuntu/Mint/Pop! OS Installation

This example is for the lightest model to run, on machines with limited resources.  See **Known-good Models** below, for other options, and adjust accordingly to your needs.

```
sudo apt-get update && sudo apt-get install -y nvidia-cuda-toolkit git git-lfs
git clone https://github.com/0cc4m/KoboldAI -b latestgptq --recurse-submodules
cd KoboldAI
./install_requirements.sh
cd KoboldAI/models
git clone https://huggingface.co/TheBloke/WizardLM-7B-uncensored-GPTQ TheBloke_WizardLM-7B-uncensored-GPTQ
cd TheBloke_WizardLM-7B-uncensored-GPTQ
ln -s WizardLM-7B-uncensored-GPTQ-4bit-128g.compat.no-act-order.safetensors 4bit-128g.safetensors
cd ../..
./play.sh
```

### Running

- The final step, running `./play.sh`, should launch your web browser.
- In the browser, click `AI`
- Click `Load a model from its directory`
- Select the model that you cloned earlier, `stable-vicuna-13B-GPTQ`
- After selecting, some sliders appear at the bottom.  Move the `GPU 0` slider all the way to the right.  NOTE: if this later fails to load, it's probably this slider that you need to change.  Read the KoboldAI docs!
- Click `Load`.
- If this loads load successfully, the Loading message should disappear within a minute or two at most.
- Now, in a separate terminal, run `kobold-assistant serve`, per the docs above.
stable-vicuna-13B-GPTQ-4bit.compat.no-act-order.safetensors 4bit-128g.safetensors


### Known-good Models

Any of these models will work.  They're listed with the easiest model to run first, and the best (but more demanding) models last.

- `TheBloke_WizardLM-7B-uncensored-GPTQ`
  - Should run within 8GB
  - Obviously not as good as the more demanding models, but surprisingly similar to Alexa and other commercial offerings
  - Run `ln -s WizardLM-7B-uncensored-GPTQ-4bit-128g.compat.no-act-order.safetensors 4bit-128g.safetensors` in the model directory before attempting to load it.

- `TheBloke/stable-vicuna-13b`
  - This should run in about 12GB
  - Seems about equivalent to Alexa
  - Run `ln -s stable-vicuna-13B-GPTQ-4bit.compat.no-act-order.safetensors 4bit-128g.safetensors` in the model directory before attempting to load it.

- `MetalX_GPT4-X-Alpasta-30b-4bit`
  - This requires at least 24GB
  - It's a capable, general model, which seems better than Alexa
  - Run `ln -s gpt4-x-alpasta-30b-128g-4bit.safetensors 4bit-128g.safetensors` in the model directory before attempting to load it.

- `TheBloke/WizardLM-30B-Uncensored-GPTQ`
  - This requires at least 24GB
  - It's a capable, general model, which seems better than Alexa
  - Run `ln -s WizardLM-30B-Uncensored-GPTQ-4bit.act-order.safetensors 4bit.safetensors` in the model directory before attempting to load it.

- Any other 4bit, 128b safetensors llama-based model from huggingface should also work, using the above approaches.


## Known-bad models

- `TheBloke/vicuna-7b-1.1-GPTQ-4bit-128g`
  - Seems to output ' \u200b' a lot, instead of a response.


## Building (for developers)

To just use it, don't do this. See the installation instructions above! But, if you want
to hack on this code:

- Install poetry per instructions
- Install and make default (via pyenv or whatever) python 3.9.16
- Run the following:

```
poetry build
poetry install
```

Now edit the files and `poetry run kobold-assistant serve` to test.


## Troubleshooting

### 'Hmm. I don't know what to say. Could you rephrase that?'

This is happens frequently right now, but is really just filler for the AI not responding
with anything. Try rephrasing as instructed. Alternatively, you could avoid repeating yourself with an encouraging instruction like "Well, try your best."

### 'ValueError:  [!] Model file not found in the output path'

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
