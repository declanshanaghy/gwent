#!/usr/bin/env bash

set -e

source ~/gwent-venv/bin/activate

ROOT=~/gwent/software

sudo apt-get install \
  ffmpeg \
  libasound2-dev libpulse-dev \
  libsdl2-dev libsmpeg-dev \
  libavformat-dev libavcodec-dev \
  libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \

# pygame stuff
#sudo apt-get install \
#  libsdl1.2-dev \
#  libsdl-image1.2-dev libsdl-ttf2.0-dev \
#  libsmpeg-dev python-numpy libportmidi-dev \
#  ffmpeg libswscale-dev libavformat-dev libavcodec-dev

pip3 install -e $ROOT/gaugette
pip3 install -e $ROOT/MFRC522-python
pip3 install -e $ROOT/gwent
#pip3 install --no-deps -e $ROOT/gwent

