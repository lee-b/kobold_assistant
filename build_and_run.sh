#!/bin/bash

rm dist/*; pip uninstall -y kobold-assistant && poetry build && pip install dist/*.whl && ./run.sh serve --debug
