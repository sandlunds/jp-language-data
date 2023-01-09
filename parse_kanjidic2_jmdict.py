# This program extracts data from JMdict and kanjidic2 in order to create json files
# that are easily consumable by a web application without access to a db or backend.
#
# It creates two types of files:
#
# kanji-index.json
# An array of length 214 where each index i corresponds to an array of all the kanji
# indexed under the radical with the number i-1. The items in that array have the
# structure of the following example:
# {
#   "literal": "元",
#   "strokeCount": 4,
#   "jouyou": true
# }
#
# <unicode code point>.json
# Contains more specific information about a certain kanji. Each object has the
# structure of the following example:
# {
#   "literal": "元"
#   "radical": 10,
#   "grade": 1,
#   "jouyou": true,
#   "strokeCount": 4,
#   "on": ["げん", "がん"],
#   "kun": ["もと"],
#   "meanings": ["beginning", "former time", "origin"],
#   "compounds": [{"word": "原価", "readings": ["げんか"], "meanings": ["cost price"]}, {...}]
# }
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import sys


def extract_kanji_from_word(word):
    return [c for c in word if ord(c) >= 0x4e00 and ord(c) <= 0x9fff]


def get_text_or_none(el, xpath):
    child = el.find(xpath)
    return child.text if child is not None else None


def get_int_or_none(el, xpath):
    child = el.find(xpath)
    return int(child.text) if child is not None else None


def parse_kanjidic2(xml):
    # Corrsponds to the two files types described in the header.
    kanji_index = [[] for x in range(214)]
    kanji_info = {}

    # For all characters in JIS X 0208 since that's the maximum supported set
    # of all the fonts we use.
    for el in xml.findall(".//character/codepoint/cp_value[@cp_type='jis208']/../.."):
        c = {}
        c['literal'] = get_text_or_none(el, "literal")
        c['radical'] = get_int_or_none(
            el, "radical/rad_value[@rad_type='classical']")
        c['grade'] = get_int_or_none(el, "misc/grade")
        c['jouyou'] = c['grade'] in [1, 2, 3, 4, 5, 6, 8]  # no, 7 is not used

        # This is a mandatory property and we don't want to
        # be None because we can't handle kanji with no stroke count.
        c['strokeCount'] = int(el.find("misc/stroke_count").text)

        c['on'] = [r.text for r in el.findall(
            "reading_meaning/rmgroup/reading[@r_type='ja_on']")]
        c['kun'] = [r.text for r in el.findall(
            "reading_meaning/rmgroup/reading[@r_type='ja_kun']")]

        # Get the meanings with no attribute (they're the english meanings)
        c['meanings'] = [m.text for m in el.findall(
            "reading_meaning/rmgroup/meaning") if len(m.keys()) == 0]

        c["compounds"] = []

        kanji_index[c['radical'] -
                    1].append({"literal": c["literal"], "jouyou": c["jouyou"], "strokeCount": c["strokeCount"]})
        kanji_info[c["literal"]] = c

    # Each sub list should be sorted by stroke count
    kanji_index_sorted = [
        sorted(g, key=lambda x: x['strokeCount']) for g in kanji_index]
    return (kanji_index_sorted, kanji_info)


def write_kanji_index(kanji_index, file):
    json.dump(kanji_index, file, ensure_ascii=False)


def write_kanji_info(kanji_info, dir):
    Path(dir).mkdir(parents=True, exist_ok=True)
    for k in kanji_info:
        info = kanji_info[k]
        filename = "0" + hex(ord(info["literal"]))[2:] + ".json"
        with open(dir + "/" + filename, "w") as f:
            json.dump(info, f, ensure_ascii=False)


output_dir = sys.argv[1]

# Parse kanjidic2
tree = ET.parse('./kanjidic2.xml')
(kanji_index, kanji_info) = parse_kanjidic2(tree)

# Parse jmdict2
# We want to find all entries with ke_pri (common words)
# Extract those keb and reb elements and get all senses
jmdict = ET.parse('./JMdict_e.xml')
entries = []
for entry in jmdict.findall("./entry"):
    keb = entry.find(".//ke_pri/../keb")

    if keb is None:
        continue

    word_info = {"readings": [], "meanings": []}
    word_info["word"] = keb.text
    for reb in entry.findall(".//re_pri/../reb"):
        word_info["readings"].append(reb.text)
    for gloss in entry.findall(".//gloss"):
        word_info["meanings"].append(gloss.text)

    for k in extract_kanji_from_word(word_info["word"]):
        if k in kanji_info:
            kanji_info[k]["compounds"].append(word_info)

with open(output_dir + "/kanji-index.json", "w") as f:
    write_kanji_index(kanji_index, f)

write_kanji_info(kanji_info, output_dir + "/kanji")
