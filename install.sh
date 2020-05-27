#!/usr/bin/env bash

set -e

source ~/gwent-venv/bin/activate

ROOT=~/gwent/software

#pip3 install $ROOT/gaugette
#pip3 install $ROOT/MFRC522-python
#pip3 install -e $ROOT/gwent
pip3 install --no-deps -e $ROOT/gwent
