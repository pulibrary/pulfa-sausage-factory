Overview
========
`main.py` takes an EAD (as the only arg, there is no CLI) and checks it for daos 
that reference PDFs. The goal is a JP2 and a TIFF for each page, plu sthe PDF,
and a METS to hold everything together. The general flow is as follows:

 * We try to download the PDF, unless @xlink:show='none'.
 * If we get a file, we extract bitmaps and try to orient them properly (via a 
   shell out to `orient_image.sh`). Orientation is only attempted on 1 and 8 bit 
   images--color tends to be mss material and the orientation script rarely 
   makes a difference.
 * Convert the bitmaps to TIFF
 * Make JP2s from the TIFFs
 * Make a METS of everything
 * Update the EAD
 * Copy the content over to its final destination

Mounts
============
The mount point should be owned by the pulfa user so that the job can be run by 
same, and not root, e.g:

Put this in /etc/fstab:

# Writable, for pulfa image harvesting
//hostname.yourdomain.edu/path/to/img/store /local/path/to/img/store smbfs rw,username={username},password={password} 0 0 

MAKE SURE, HOWEVER, THAT THESE ARE NOT MOUNTED WHILE YOU DO THE FOLLOWING:

Then:
1. Make a pulfa user on the machine that will run this app
1. Edit /etc/passwd and /etc/group so that the values for uid and gid on the 
   local machine are the same as as the dps user on libserv64 (501 and 501, 
   respectively).
1. If you do an ls -l on /home you will see that the pulfa folder is no longer 
   owned by pulfa but by the numeric values for uid and gid that were previously 
   in /etc/passwd and /etc/group.  So, you want to change ownership back to 
   pulfa. 
1. cd /home
1. chown -R pulfa:pulfa pulfa

Now mount:
1. su pulfa
1. mkdir -p /local/path/to/image/store
1. sudo mount -a (become a sudoer if necessary)
1. As the pulfa change to the mounted directories and test permissions - you 
   shouldn't need to sudo anything. 

Dependencies
============
Note that hard-coded paths to these utilities are required in the bash scripts
themselves and in `/etc/main.conf`. Note that these are in addition to the 
regular Python 'batteries included' and common *nix utilities. It's probably a 
good idea to just check them all, __at least__ in the case of the Bash scripts.

`main.py`:
 * libxml2 (and python bindings; generally on ubuntu systems)
 * requests: apt-get install python-pip, then pip install requests
 * convert: apt-get install imagemagick
 * pdfimages: apt-get install poppler-utils
 * pyexiv2: apt-get install  python-pyexiv2
 * Java

`dao.py`:
* libxml2 (and python bindings; generally on ubuntu systems) 

`orient_image.sh`:
 * ocrad (apt-get install ocrad)
 * convert (apt-get install imagemagick)
 * aspell (apt-get install aspell)
