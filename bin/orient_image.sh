#!/bin/bash

# There's enough going on here that we're just going to leave this in a 
# separate file.

file=$1

TMP="/tmp/pulfa/img_harvester/rotation-calc"
# Clean up if there are files from the last run
# (leaving them around is handy for debugging)
if [ -d $TMP ]; then
	rm -r $TMP
fi
mkdir $TMP

# Dependencies:                                                                 
# convert: apt-get install imagemagick                                          
# ocrad: sudo apt-get install ocrad                                               

ASPELL="/usr/bin/aspell"
AWK="/usr/bin/awk"
BASENAME="/usr/bin/basename"
CONVERT="/usr/bin/convert"
DIRNAME="/usr/bin/dirname"
HEAD="/usr/bin/head"
OCRAD="/usr/bin/ocrad" # apt-get install ocrad
SORT="/usr/bin/sort"
WC="/usr/bin/wc"

# Make 90 degree variants of the input file. The input file is north
file_name=$(basename $file)
north_file="$TMP/$file_name-north"
east_file="$TMP/$file_name-east"
south_file="$TMP/$file_name-south"
west_file="$TMP/$file_name-west"

# TODO: despeckle doesn't seem to help. Anything else from imagemagick?

cp  $file $north_file
$CONVERT -rotate 90 $file $east_file
$CONVERT -rotate 180 $file $south_file
$CONVERT -rotate 270 $file $west_file

# OCR each.
# A note about the OCR engine: I would like to be Tesseract, but the version
# in Synaptic is not supported on 64 bit machines, and I'm not about to build
# from source right now. Tesseract 3.01 is alleged to work on 64 bit 
# architecture.
# links: http://code.google.com/p/leptonica/downloads/list,
#		 http://code.google.com/p/tesseract-ocr/downloads/list		
# 
# Tesseract does Unicode (gocr is ascii only), and we could pass languages,
# etc.
# 
# For a good comparison, @see http://www.mscs.dal.ca/~selinger/ocr-test
north_text="$north_file.txt"
east_text="$east_file.txt"
south_text="$south_file.txt"
west_text="$west_file.txt"

$OCRAD -f -F utf8 $north_file -o $north_text
$OCRAD -f -F utf8 $east_file -o $east_text
$OCRAD -f -F utf8 $south_file -o $south_text
$OCRAD -f -F utf8 $west_file -o $west_text

# Get the word count for each txt file (least 'words' = least whitespace junk)
wc_table="$TMP/wc_table"
echo "$($WC -w $north_text) $north_file" > $wc_table
echo "$($WC -w $east_text) $east_file" >> $wc_table
echo "$($WC -w $south_text) $south_file" >> $wc_table
echo "$($WC -w $west_text) $west_file" >> $wc_table

# Take the bottom two; these are likely right side up and upside down, but 
# generally too close to call beyond that.
bottom_two_wc_table="$TMP/bottom_two_wc_table"
$SORT -n $wc_table | $HEAD -2 > $bottom_two_wc_table

# Spellcheck. The lowest number of misspelled words is most likely the 
# correct orientation.
misspelled_words_table="$TMP/misspelled_words_table"
while read record; do
	txt=$(echo $record | $AWK '{ print $2 }')
	misspelled_word_count=$(cat $txt | $ASPELL -l en list | wc -w)
	echo "$misspelled_word_count $record" >> $misspelled_words_table
done < $bottom_two_wc_table

# Do the sort, overwrite the input file, save out the text
winner=$($SORT -n $misspelled_words_table | $HEAD -1)
rotated_file=$(echo $winner | $AWK '{ print $4 }')

mv $rotated_file $file

