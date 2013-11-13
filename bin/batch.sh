#!/bin/bash

#
# Does svn update then uses find to look at all EADs modified since the last 
# run. Runs main.sh for each, and then checks back into svn.
#

#TODO: we chown mets to a regular user if this is run as root before checking 
# them in.

FIND=/usr/bin/find
SVN=/usr/bin/svn
PYTHON=/usr/bin/python

LAST_RUN=.last_run

EADS_ROOT="/home/pulfa/data/eads"
METS_ROOT="/home/pulfa/data/mets"

# update
$SVN update $DATA_ROOT

# build the find command
find_cmd="$FIND $EADS_ROOT -name *.xml"
if [ -e $LAST_RUN ]; then
	find_cmd = "$find_cmd -newer $LAST_RUN"
fi

# do
for ead in $($find_cmd); do
	$PYTHON ./main.py $ead
done

$SVN ci $EADS_ROOT -m "[cron] PDFs harvested, daos replaces with METS."
$SVN add $METS_ROOT/*
$SVN add $METS_ROOT/*/*
$SVN ci $METS_ROOT -m "[cron] Initial commit."

touch $LAST_RUN

