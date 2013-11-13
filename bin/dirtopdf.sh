#!/bin/bash

#
# Takes a directory of TIFF images and makes a PDF
#
# Usage:
#  ./dirtopdf [-rd] [-s <arg>] -o <file> <dir>
#
# e.g.: ./dirtopdf.sh -rd -s 3200 -o new.pdf /tmp/bar
# sh ./dirtopdf.sh -d -s 3200 -o /usr/share/images/libserv64/vol2/pudl/C0022/c0018.pdf /usr/share/images/libserv37/dps/C0022/c0018/
#
# Optional params:
#  -s Resize the images to <arg>.
#
# Options:
#  -r Do so recursively
#  -d Show a bunch of debugging output
#

PDFTK="/usr/bin/pdftk"
CONVERT="/usr/bin/convert"

TMP="/tmp/dirtopdf"

OUTPUT=""
RESIZE=""
RECURSIVE=1
SHOW_DEBUG_OUTPUT=1

while getopts ":rds:o:" opt; do
	case $opt in
		r)
			RECURSIVE=0
		;;
		d)
			SHOW_DEBUG_OUTPUT=0
		;;
		s)
			RESIZE=$OPTARG
		;;
		o)
			OUTPUT=$OPTARG
		;;
		:)
			echo "Option -$OPTARG requires an argument." >&2
			exit 1
		;;
		\?)
			echo "Not an option: -$OPTARG" >&2
			exit 1
		;;
	esac
done

# require -o
if [ "x" == "x$OUTPUT" ]; then
	echo "-o <output file> is required"
	exit 1
fi

shift $((OPTIND-1))
DIR=$1

#get the absolute path to $DIR
DIR=$(cd $DIR; pwd)

if [ $SHOW_DEBUG_OUTPUT == 0 ]; then
	echo "[DEBUG] Input directory: $DIR"
	echo "[DEBUG] Output file: $OUTPUT"
	echo "[DEBUG] Will resize to $RESIZE"
	if [ $RECURSIVE == 0 ]; then
		echo "[DEBUG] Will work recursively"
	else
		echo "[DEBUG] Will work on files in $DIR only"
	fi
fi

FIND_CMD="find $DIR -type f -name '*.tif' ! -name '.*'"
#FIND_CMD="find $DIR ! -regex '.*/\..*' -type f -name '*.tif'"
if [ $RECURSIVE == 1 ]; then
	FIND_CMD="$FIND_CMD -maxdepth 1"
fi


if [ $SHOW_DEBUG_OUTPUT == 0 ]; then echo "FIND_CMD: $FIND_CMD"; fi

#make a temporary directory:
if [ ! -d $TMP	]; then
	mkdir $TMP
	if [ $SHOW_DEBUG_OUTPUT == 0 ]; then 
		echo "Made: $TMP"
	fi
fi

i=1
for in_img in $(eval $FIND_CMD | sort); do
	# convert to a single page pdf
	out=$(printf "$TMP/%08d.pdf" $i)

	# see http://www.imagemagick.org/script/command-line-options.php#density
	cvt="$CONVERT -density 200x200"
	if [ "x$RESIZE" != "x"  ]; then
		cvt="$cvt -resize $RESIZE"x"$RESIZE"
	fi
	cvt="$cvt -colorspace Gray -compress JPEG -quality 60 $in_img $out"
	
	if [ $SHOW_DEBUG_OUTPUT == 0 ]; then 
		echo $cvt
	fi

	$cvt

	let "i += 1"
done

pdftk_cmd="$PDFTK"
for f in $(find $TMP -name "*.pdf" | sort); do
	pdftk_cmd=$"$pdftk_cmd $f"
done
pdftk_cmd="$pdftk_cmd cat output $OUTPUT"

$pdftk_cmd

if [ $SHOW_DEBUG_OUTPUT == 0 ]; then 
	echo $pdftk_cmd
fi

rm $TMP/*

exit 0
