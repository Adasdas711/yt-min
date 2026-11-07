"""Structural checks for the packaged stroke-ready Cyrillic font (fonttools)."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

path=Path(__file__).resolve().parents[1]/'src/assets/fonts/MinimalCondensed-BlackItalic.ttf'
font=TTFont(path)
assert 'fvar' not in font, 'Ship the actual Black instance, not variable construction paths'
assert font['OS/2'].usWeightClass==900
cmap=font.getBestCmap();glyphs=font.getGlyphSet()
for char in 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя':
    assert ord(char) in cmap, char
# These letters have one exterior boundary, plus only their real letter holes.
# Extra closed paths produce the visible bars/triangles from the reported bug.
for char,expected in {'Л':1,'Д':2,'Е':1,'Н':1,'О':2,'А':2,'Б':2,'Р':2,'С':1,'Т':1}.items():
    pen=DecomposingRecordingPen(glyphs);glyphs[cmap[ord(char)]].draw(pen)
    contours=sum(command=='closePath' for command,_ in pen.value)
    assert contours==expected,(char,contours,expected)
print('PASS static Black Italic font covers Cyrillic, with unified contours and only real letter holes')
