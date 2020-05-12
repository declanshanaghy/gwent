#!/usr/bin/env bash

set -e

source ~/venv-gwent/bin/activate

cd ~/gwent/software/py3
pip3 install --no-deps -e .
