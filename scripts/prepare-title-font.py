"""Prepare the packaged Cyrillic outline font from Roboto Condensed Italic.

Usage: python scripts/prepare-title-font.py /path/to/RobotoCondensed-Italic.ttf
Development dependencies: fonttools, skia-pathops. The source variable font is
RobotoCondensed-Italic[wght].ttf from google/fonts/ofl/robotocondensed, SIL OFL.
No font processing or external font requests happen in the extension at runtime.
"""
import argparse
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import removeOverlaps
from fontTools.varLib.instancer import instantiateVariableFont

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
args = parser.parse_args()
font = instantiateVariableFont(TTFont(args.source), {'wght': 900}, inplace=True)
# Variable fonts keep overlapping construction paths. CSS text-stroke outlines
# every path, exposing bars inside Cyrillic letters; union them before shipping.
removeOverlaps(font, removeHinting=True)
for name_id, value in {
    1: 'Minimal Condensed', 2: 'Black Italic',
    3: 'MinimalCondensed-BlackItalic-1.0', 4: 'Minimal Condensed Black Italic',
    6: 'MinimalCondensed-BlackItalic', 16: 'Minimal Condensed', 17: 'Black Italic',
}.items():
    font['name'].setName(value, name_id, 3, 1, 0x409)
    font['name'].setName(value, name_id, 1, 0, 0)
font.recalcTimestamp = False
font['head'].modified = 3786912000  # Reproducible 2024-01-01 OpenType timestamp.
output = Path(__file__).resolve().parents[1]/'src/assets/fonts/MinimalCondensed-BlackItalic.ttf'
font.save(output)
print(output)
