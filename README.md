# Language data

## Generate json from source data

1. Create a directory called `generated`.

2. Run the following command to generate radical data:

    $ csvtojson --delimiter=";" --checkType=true japanese-radicals.csv > generated/japanese-radicals.json

3. Run the following command to generate kanji data:

    $ python parse_kanjidic2_jmdict.py generated

