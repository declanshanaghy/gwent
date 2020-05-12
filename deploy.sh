#!/usr/bin/env bash

set -e

source ~/gwent-venv/bin/activate

cd ~/gwent/software/gaugette
pip3 install --no-deps -e .

cd ~/gwent/software/gwent
pip3 install --no-deps -e .
