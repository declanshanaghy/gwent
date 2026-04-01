"""Shared data directory paths for sfx, music, and recordings."""
import os

# software/data/ relative to this file (gwent/game/data_paths.py → ../../data/)
_DATA_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data'))

SFX_DIR = os.path.join(_DATA_ROOT, 'sfx')
MUSIC_DIR = os.path.join(_DATA_ROOT, 'music')
RECORDINGS_DIR = os.path.join(_DATA_ROOT, 'recordings')
