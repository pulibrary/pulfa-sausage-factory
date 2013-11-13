#!/usr/bin/env python

#===============================================================================
# PULFA PDF Harvester
# Trolls EADs for links to PDFs, and, where possible:
#  * downloads the file
#  * extracts TIFFs
#  * creates a JP2 from each TIFF
#  * summarizes all of this in a METS
#  * updates the EAD with revised links
#
# @author: <a href="jstroop@princeton.edu">Jon Stroop</a>
# @since: Tue May 29 2012
#
# Dependencies:
#  * libxml2 (and python bindings; generally on ubuntu systems)
#  * requests http://docs.python-requests.org/en/latest/index.html (pip install requests)
#  * ocrad (apt-get install ocrad)
#  * convert (apt-get install imagemagick)
#  * pdfimages (apt-get install poppler-utils)
#  * pyexiv2 (apt-get install  python-pyexiv2)
#
#===============================================================================

from PIL import Image
from reportlab.pdfgen import pdfimages
from string import zfill
from sys import exit, argv
from shutil import copy
import ConfigParser
import hashlib
import libxml2
import logging
import logging.config
import os
import requests
import subprocess
import re

def normalize_whitespace(str):
	str = str.strip()
	str = re.sub(r'\s+', ' ', str)
	return str

class Pdf():
	"""
	Just a set of data attributes we collect about pdfs through the process. 
	"""
	def __init__(self):
		self.src_url = None
		self.host_c_id = None
		self.pdf_title = None
		self.pdf_local_path = None
		self.pdf_resp_status = None
		self.pdf_idx = None # index of this pdf's dao relative to the parent ead:did
		self.bitmaps_dir = None
		self.img_bits = None # 1, 8 or 24
		self.tiffs_dir = None
		self.jp2s_dir = None
		self.mets_path = None
		self.mets_uri = None
		
	def __str__(self):
		keys = self.__dict__.keys()
		keys.sort()
		props = []
		for k in keys:
			props.append(str(self.__dict__.get(k)))
		return '%%'.join(props)
	
	@staticmethod
	def slurp(path):
		"""
		Given a text file (incl. a header row) of Pdf object properties, return
		a list of Pdf objects.
		"""
		pdfs = []
		try:
			report = open(path, 'r')
			properties_hdr = []
			c = 0
			for line in report:
				line = line.strip()
				if c == 0: 
					properties_hdr = [prop for prop in line.split('%%')]
				else:
					d = 0
					pdf = Pdf()
					for prop in line.split('%%'):
						pdf.__dict__[properties_hdr[d]] = prop
						d += 1
					pdfs.append(pdf)
				c += 1
		finally:			
			report.close()
		
		return pdfs

	
	@staticmethod
	def serialize(path, pdfs):
		"""
		Given a list Pdf objects, serialize them to the file at the path parameter.
		"""
		dir = os.path.dirname(path)
		if not os.path.exists(dir):
			os.makedirs(dir, 0755)
			logr.debug("made: " + dir)
			
		report_file = open(path, 'w')
		
		# header
		keys = pdfs[0].__dict__.keys()
		keys.sort()
		report_file.write("%%".join(keys) + '\n')
		
		for pdf_obj in pdfs:
			report_file.write(pdf_obj.__str__() + '\n')
		report_file.close()

def get_pdfs(ead_path):
	try:
		doc = libxml2.parseFile(ead_path)
		ctxt = doc.xpathNewContext()
		ctxt.xpathRegisterNs('xlink', _XLINK_NS)
		ctxt.xpathRegisterNs('ead', _EAD_NS)
		
		eadid = ctxt.xpathEval("//ead:eadid")[0].content
		
		pdf_objs = []
		
		#TODO: test this - skipping daos that don't have a METS following
		daos = ctxt.xpathEval("""
			//ead:dao[
				contains(@xlink:href, '.pdf')
				and not(contains(@xlink:href, '/Accessions/'))
				and not(@xlink:show='none') 
				and not(./following-sibling::ead:dao[@xlink:role='" + _METS_NS + "'])
			]
			""")
		if daos != []:
			for pdf_dao in daos:
				# initialize a Pdf object
				logr.debug("---------------------------------------------------------------------------")
				pdf_obj = Pdf()
				pdf_obj.src_url = str(pdf_dao.nsProp("href", _XLINK_NS))
				logr.debug("src_url: " + pdf_obj.src_url)
	
				title_xpath = "//ead:did[ead:dao[@xlink:href='" + pdf_obj.src_url + "']]/ead:unittitle[1]"
				date_xpath = "//ead:did[ead:dao[@xlink:href='" + pdf_obj.src_url + "']]/ead:unitdate[1]"
				title_date_xpath = "concat(" + title_xpath + ", ', ', " + date_xpath + ")"
				
				logr.debug('title_date_xpath: ' + title_date_xpath)
				
				title = ctxt.xpathEval(title_date_xpath)
				title = title.replace('"', '&quot;').replace("'", '&apos;')
				pdf_obj.pdf_title = normalize_whitespace(title)
				logr.debug('pdf_obj.pdf_title: ' + pdf_obj.pdf_title)
	
				# check if we have preceding daos for pdfs, in which case we need to add an index number onto the file name below
				idx_xpath = "count(//ead:dao[@xlink:href='"
				idx_xpath = idx_xpath + pdf_obj.src_url
				idx_xpath = idx_xpath + "']/preceding-sibling::ead:dao[contains(@xlink:href, '.pdf')])"
	
				pdf_obj.pdf_idx = int(ctxt.xpathEval(idx_xpath))
				
				# get the ID of the host component id			
				pdf_obj.host_c_id = pdf_dao.parent.parent.prop('id') 			
				logr.debug("host_c_id: " + pdf_obj.host_c_id)			
				
				# try to download the PDF
				req = requests.get(pdf_obj.src_url) 
				pdf_obj.pdf_resp_status = req.status_code
				logr.debug("pdf_resp_status: " + str(pdf_obj.pdf_resp_status))
				
				if pdf_obj.pdf_resp_status == 200:
					
					# e.g. MC216_c003 -> $PDFS_LOCAL_ROOT/MC216/c003[.idx].pdf
					pdf_obj.pdf_local_path = os.path.join(PDFS_LOCAL_ROOT, pdf_obj.host_c_id.replace('_', '/'))
					if pdf_obj.pdf_idx > 0: pdf_obj.pdf_local_path = pdf_obj.pdf_local_path + '_' + str(pdf_obj.pdf_idx)
					pdf_obj.pdf_local_path = pdf_obj.pdf_local_path + ".pdf"
					logr.debug('pdf_local_path: ' + pdf_obj.pdf_local_path)
					
					if not os.path.exists(pdf_obj.pdf_local_path):
						# make the storage dir
						dir = os.path.dirname(pdf_obj.pdf_local_path)
						if not os.path.exists(dir):
							os.makedirs(dir, 0755)
							logr.debug("made: " + dir)
						
						f = open(pdf_obj.pdf_local_path, 'w')
						f.write(req.content)
						f.close()
	
					else:
						logr.warn("file: " + pdf_obj.pdf_local_path + " exists; no further action.")
				
				
				# add the object to the list 
				pdf_objs.append(pdf_obj)
		else:
			logr.info("No (new) PDFs found in " + eadid + ". Will exit.")
			exit(0)
			
	finally:
		ctxt.xpathFreeContext()
		doc.freeDoc()

	return pdf_objs
	
def extract_bitmaps_from_pdf(pdf_obj):
	"""
	Extract bitmaps from a PDF.
	"""
	if int(pdf_obj.pdf_resp_status) == 200 and os.path.exists(pdf_obj.pdf_local_path):
		
		# figure out the path to the output dir
		pdf_obj.bitmaps_dir = os.path.join(BITMAPS_ROOT, pdf_obj.host_c_id.replace('_', os.sep))
		if int(pdf_obj.pdf_idx) > 0: 
			pdf_obj.bitmaps_dir = pdf_obj.bitmaps_dir + '_' + pdf_obj.pdf_idx
		pdf_obj.bitmaps_dir = pdf_obj.bitmaps_dir + os.sep
		logr.debug('bitmaps_dir for ' + pdf_obj.host_c_id + ": " + pdf_obj.bitmaps_dir)
		
		# make the output dir if necessary
		if not os.path.exists(pdf_obj.bitmaps_dir):
			os.makedirs(pdf_obj.bitmaps_dir, 0755)
			logr.debug('made: ' + pdf_obj.bitmaps_dir)
		else:
			logr.debug('exists: ' + pdf_obj.bitmaps_dir)
		
		# don't generate if the directory is not empty
		if len(os.listdir(pdf_obj.bitmaps_dir)) > 0:
			logr.error('not empty: ' + pdf_obj.bitmaps_dir)
			logr.error('skipping ' + pdf_obj.pdf_local_path)
		else:
			# build the command
			pdfimages_cmd = PDFIMAGES + " " + pdf_obj.pdf_local_path + " " + pdf_obj.bitmaps_dir + 'x'
			logr.debug('pdfimages_cmd: ' + pdfimages_cmd)
			
			# execute 
			pdfimgage_proc = subprocess.Popen(pdfimages_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			exit_code = pdfimgage_proc.wait()
			logr.debug('exit: ' + str(exit_code))
			 
			for line in pdfimgage_proc.stdout:
				logr.debug(line.rstrip())
				
			for line in pdfimgage_proc.stderr:
				logr.error(line.rstrip()) 
	else:
		logr.debug(pdf_obj.src_url + " was not downloaded and/or does not exist on the filesystem")

def bitmaps_to_tiff(pdf_obj, rm_bitmaps=True):
	
	if int(pdf_obj.pdf_resp_status) == 200 and os.path.exists(pdf_obj.bitmaps_dir):
		# figure out the path to the output dir
		pdf_obj.tiffs_dir = os.path.join(TIFFS_LOCAL_ROOT, pdf_obj.host_c_id.replace('_', os.sep))
		if int(pdf_obj.pdf_idx) > 0: 
			pdf_obj.tiffs_dir = pdf_obj.tiffs_dir + '_' + pdf_obj.pdf_idx
		pdf_obj.tiffs_dir = pdf_obj.tiffs_dir + os.sep
		logr.debug('tiffs_dir for ' + pdf_obj.host_c_id + ": " + pdf_obj.tiffs_dir)
		
		# make the output dir if necessary
		if not os.path.exists(pdf_obj.tiffs_dir):
			os.makedirs(pdf_obj.tiffs_dir, 0755)
			logr.debug('made: ' + pdf_obj.tiffs_dir)
		 
		c = 1
		files = os.listdir(pdf_obj.bitmaps_dir)
		files.sort()
		for bmp in files:
			bmp = os.path.join(pdf_obj.bitmaps_dir, bmp)
			file_ext = os.path.splitext(bmp)[1]
			if file_ext == '.pbm':
				pdf_obj.img_bits = 1
			elif file_ext == '.pgm':
				pdf_obj.img_bits = 8
			else:
				pdf_obj.img_bits = 24
			
			tiff_name = os.path.join(pdf_obj.tiffs_dir, str(c).zfill(8) + '.tif')
			if not os.path.exists(tiff_name):
				# rotate if text-based (generally bitonal or grayscale)
				if pdf_obj.img_bits != 24:
					rotate_cmd = _BIN + os.sep + 'orient_image.sh ' + bmp
					logr.debug('rotate_cmd: ' + rotate_cmd)
					# (build the command)	
					rotate_proc = subprocess.Popen(rotate_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					exit_code = rotate_proc.wait()
					logr.debug('exit: ' + str(exit_code))
					 
					for line in rotate_proc.stdout:
						logr.debug(line.rstrip())
					for line in rotate_proc.stderr:
						logr.error(line.rstrip()) 
				
				# convert
				
				# figure out the long dimension, we want a multiple of 100
				img_file = open(bmp, 'r')
				im = Image.open(img_file)
				long_side = max(im.size)
				rounded = int(round(long_side, -2))
				if rounded > long_side: rounded = rounded - 100
				resize = str(rounded) + 'x' + str(rounded) + '\>'
				img_file.close()
				
				# (build the command)
				convert_cmd = CONVERT + ' ' + bmp + ' -resize ' + resize + ' -quality 100 '
				if pdf_obj.img_bits == 24: convert_cmd = convert_cmd + '-profile ' + SRGB_PROFILE + ' '
				else: convert_cmd = convert_cmd + '-depth 8 -profile ' + GRAY_PROFILE + ' '
				convert_cmd = convert_cmd + tiff_name
				logr.debug('convert_cmd: ' + convert_cmd)
				
				convert_proc = subprocess.Popen(convert_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				exit_code = convert_proc.wait()
				logr.debug('exit: ' + str(exit_code))
				
				for line in convert_proc.stdout:
					logr.debug(line.rstrip())
				for line in convert_proc.stderr:
					logr.error(line.rstrip())
			
				# delete the bitmap
				if rm_bitmaps: 
					os.remove(bmp)
				else:
					logr.warn("rm_bitmaps set to False. This is intended for debugging and will fill the disk quickly.")
			
			else:
				logr.error(tiff_name + ' already exists, will not regenerate.')
			
			c += 1
		
		# delete the bitmap dir
		if rm_bitmaps:
			for f in os.listdir(pdf_obj.bitmaps_dir):
				f = os.path.join(pdf_obj.bitmaps_dir, f)
				os.remove(f)
			os.rmdir(pdf_obj.bitmaps_dir)
		else:
			logr.warn("rm_bitmaps set to False. This is intended for debugging and will fill the disk quickly.")
	
def tiffs_to_jp2(pdf_obj):
	
	if int(pdf_obj.pdf_resp_status) == 200 and os.path.exists(pdf_obj.tiffs_dir):
		# figure out the path to the output dir
		pdf_obj.jp2s_dir = os.path.join(JP2S_ROOT, pdf_obj.host_c_id.replace('_', os.sep))
		
		if int(pdf_obj.pdf_idx) > 0: 
			pdf_obj.jp2s_dir = pdf_obj.jp2s_dir + '_' + pdf_obj.pdf_idx
			
		pdf_obj.jp2s_dir = pdf_obj.jp2s_dir + os.sep
		logr.debug('jp2s_dir for ' + pdf_obj.host_c_id + ": " + pdf_obj.jp2s_dir)
		
		# make the output dir if necessary
		if not os.path.exists(pdf_obj.jp2s_dir):
			os.makedirs(pdf_obj.jp2s_dir, 0755)
			logr.debug('made: ' + pdf_obj.jp2s_dir)
	
		
		files = os.listdir(pdf_obj.tiffs_dir)
		files.sort()
		for tiff in files:
			jp2 = tiff.replace(os.path.splitext(tiff)[1], ".jp2")
			jp2 = os.path.join(pdf_obj.jp2s_dir, jp2)
			
			if not os.path.exists(jp2):
				tiff = os.path.join(pdf_obj.tiffs_dir, tiff)
		
				# figure out the # of levels
				img_file = open(tiff, 'r')
				im = Image.open(img_file)
				size = max(im.size)
				img_file.close()
				
				level_dim = int(size)
				min = 96
				levelcount = 0
				while level_dim >= min:
					levelcount += 1
					level_dim = level_dim / 2
					
				logr.debug('long side: ' + str(size))
				logr.debug('levels: ' + str(levelcount))
				
				# build the command
				compress_cmd = _BIN + os.sep + 'kdu_compress -i ' + tiff + ' -o ' + jp2 + ' '
				compress_cmd = compress_cmd + '-rate 1.2,0.7416334477,0.4583546103,0.2832827752,0.1750776907,0.1082041271,0.0668737897,0.0413302129 Clayers=8 '
				compress_cmd = compress_cmd + 'Clevels=' + str(levelcount) + ' '
				compress_cmd = compress_cmd + 'Cuse_precincts=yes Cprecincts=\{256,256\} Cblk=\{64,64\} Cuse_sop=yes '
				compress_cmd = compress_cmd + 'Cuse_eph=yes Corder=RPCL ORGgen_plt=yes ORGtparts=R Stiles=\{256,256\} '
				if pdf_obj.img_bits == 24: compress_cmd = compress_cmd + '-jp2_space sRGB '
				compress_cmd = compress_cmd + '-double_buffering 10 -num_threads 4 -no_weights ' # -quiet
				logr.debug('compress_cmd: ' + compress_cmd)
				
				# execute
				compress_proc = subprocess.Popen(compress_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_ENV)
				exit_code = compress_proc.wait()
				logr.debug('exit: ' + str(exit_code))
				 
				for line in compress_proc.stdout:
					logr.debug(line.rstrip())
				for line in compress_proc.stderr:
					logr.error(line.rstrip())
	
				logr.debug('')
				
			else:
				logr.error(jp2 + ' exists; will not regenerate.')
		
	
def pdf_obj_to_mets(pdf_obj):
	# make the METS, calculate file sizes 
	if int(pdf_obj.pdf_resp_status) == 200 and os.path.exists(pdf_obj.jp2s_dir):
		
		# figure out the local path
		pdf_obj.mets_path = os.path.join(METS_ROOT, pdf_obj.host_c_id.replace('_', os.sep))
		if int(pdf_obj.pdf_idx) > 0: 
			pdf_obj.mets_path = pdf_obj.mets_path + '_' + pdf_obj.pdf_idx
			
		pdf_obj.mets_path = pdf_obj.mets_path + '.mets'
		logr.debug('METS path for ' + pdf_obj.host_c_id + ": " + pdf_obj.jp2s_dir)
				
		# make the dir if necessary
		dir = os.path.dirname(pdf_obj.mets_path)
		if not os.path.exists(dir):
			os.makedirs(dir, 0755)
			logr.debug('made: ' + dir) 
		
		# build the command. We're shelling out to a bit of old python code 
		# that I can't bear to visit again.
		objid = pdf_obj.host_c_id.replace('_', '/')
		if int(pdf_obj.pdf_idx) > 0: 
			objid = objid + '_' + pdf_obj.pdf_idx
			
		pdf_obj.mets_uri = pdf_obj.mets_path.replace(METS_ROOT, 'http://findingaids.princeton.edu/folders')
		
		tmp_out = TMP_DIR + os.sep + 'folder.xml'
		
		dao_cmd = PYTHON + ' ' + _BIN + os.sep + 'dao.py '
		dao_cmd = dao_cmd + '--output ' + tmp_out + ' '
		dao_cmd = dao_cmd + '--objid ' + objid + ' '
		dao_cmd = dao_cmd + '--docid ' + pdf_obj.mets_uri + ' '
		for input in (pdf_obj.pdf_local_path, pdf_obj.tiffs_dir[:-1], pdf_obj.jp2s_dir[:-1]): # trailing slashes we causing problems
			dao_cmd = dao_cmd + '--input ' + input + ' '
		
		logr.debug('dao_cmd: ' + dao_cmd)
		
		# execute
#		dao_proc = subprocess.Popen(dao_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		dao_proc = subprocess.Popen(dao_cmd, shell=True)
		exit_code = dao_proc.wait()
		logr.debug('exit: ' + str(exit_code))
			 
#		for line in dao_proc.stdout:
#			logr.debug(line.rstrip())
#		for line in dao_proc.stderr:
#			logr.error(line.rstrip())
		
		
		# xslt: subprocess this:
		saxon_cmd = JAVA + ' -jar ' + _LIB + os.sep + 'saxon9he.jar ' 
		saxon_cmd = saxon_cmd + '-xsl:' + _LIB + os.sep + 'folder2mets.xsl '
		saxon_cmd = saxon_cmd + '-s:' + tmp_out + ' -o:' + pdf_obj.mets_path + ' '
		saxon_cmd = saxon_cmd + 'title="' + pdf_obj.pdf_title + '"'
		logr.debug('saxon_cmd: ' + saxon_cmd)
		
		saxon_proc = subprocess.Popen(saxon_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		exit_code = saxon_proc.wait()
		logr.debug('exit: ' + str(exit_code))
			 
		for line in saxon_proc.stdout:
			logr.debug(line.rstrip())
		for line in saxon_proc.stderr:
			logr.error(line.rstrip())
		


def update_ead(ead_path, pdf_objs):
	doc = libxml2.parseFile(ead_path)
	root = doc.getRootElement()
	xlink_ns = root.searchNsByHref(doc, _XLINK_NS)
	ead_ns = root.searchNsByHref(doc, _EAD_NS)

	ctxt = doc.xpathNewContext()
	ctxt.xpathRegisterNs('xlink', _XLINK_NS)
	ctxt.xpathRegisterNs('ead', _EAD_NS)
	try:
		for pdf_obj in pdf_objs:
			src_dao_xpath = "//ead:dao[@xlink:href='" + pdf_obj.src_url + "'][1]"
			logr.debug('src_dao_xpath: ' + src_dao_xpath)
			src_dao = ctxt.xpathEval(src_dao_xpath)[0]
			# check the object:
			if pdf_obj.pdf_resp_status == '401':
				# xlink:show="none" to existing dao. Log it.
				logr.info(pdf_obj.src_url + ' returned a 401 (Unauthorized).')
				src_dao.setNsProp(xlink_ns, 'show', 'none')
				logr.info('xlink:show="none" has been added to the dao')
				doc.saveFormatFileEnc(ead_path, "UTF-8", 1)
				
			elif pdf_obj.pdf_resp_status == '404':
				logr.error(pdf_obj.src_url + ' returned a 404 (Not Found).')
				src_dao.setNsProp(xlink_ns, 'show', 'none')
				logr.warn('xlink:show="none" has been added to the dao')
				doc.saveFormatFileEnc(ead_path, "UTF-8", 1)
				
			elif pdf_obj.pdf_resp_status == '200':
				all_accounted_for = True
				for part in (pdf_obj.pdf_local_path, pdf_obj.mets_path, pdf_obj.tiffs_dir, pdf_obj.jp2s_dir):
					if not os.path.exists(part):
						all_accounted_for = False
						logr.error('Missing: ' + part)
					elif os.path.isdir(part):
						if len(os.listdir(part)) == 0:
							all_accounted_for = False
							logr.error(part + ' exists but is empty')
							
				if all_accounted_for:
#					Add an additional dao					
#					new_dao = libxml2.newNode('dao')
#					new_dao.setNs(ead_ns)
#					new_dao.setNsProp(xlink_ns, 'role', _METS_NS)
#					new_dao.setNsProp(xlink_ns, 'href', pdf_obj.mets_uri)
#					src_dao.addNextSibling(new_dao)
					
					# Revise the existing dao
					src_dao.setNsProp(xlink_ns, 'role', _METS_NS)
					src_dao.setNsProp(xlink_ns, 'href', pdf_obj.mets_uri)
					
					logr.debug('Modified PDF dao: ' + str(src_dao))
					doc.saveFormatFileEnc(ead_path, "UTF-8", 1)
				else:
					logr.error('dao ' + pdf_obj.src_url + ' will not be changed')
				# check the object, if all is good, append a new dao
				# we ultimately want to replace, but not until pulfa 1.0 is out of prod.
			else:
	 			logr.error('Unhandled HTTP response (' + pdf_obj.pdf_resp_status + ') for ' + pdf_obj.src_url)
	finally:
		ctxt.xpathFreeContext()
		doc.freeDoc()
			
def finalize(pdf_objs):
	# TODO: move the files to their permanent homes, carefully asserting that 
	# they're not overwriting anything (if not os.path.exists(dest): <copy>)
	for pdf_obj in pdf_objs:

		all_parts_exist = True
		for part in (pdf_obj.pdf_local_path, pdf_obj.mets_path, pdf_obj.tiffs_dir, pdf_obj.jp2s_dir):
			if not os.path.exists(part): 
				all_parts_exist = False
				logr.error(pdf_obj.host_c_id + ' will not be moved because ' + part + ' is missing')


		if all_parts_exist:
			final_pdf = pdf_obj.pdf_local_path.replace(PDFS_LOCAL_ROOT, PDFS_FINAL_ROOT)
			logr.debug('final_pdf: ' + final_pdf)
			final_tiff_dir = pdf_obj.tiffs_dir.replace(TIFFS_LOCAL_ROOT, TIFFS_FINAL_ROOT)
			logr.debug('final_tiff_dir: ' + final_tiff_dir)
			
			# PDF
			pdf_final_dir = os.path.dirname(final_pdf)
			if not os.path.exists(pdf_final_dir):
				os.makedirs(pdf_final_dir, 0755)
				logr.info("Made " + pdf_final_dir)
				
			if not os.path.exists(final_pdf):
				copy(pdf_obj.pdf_local_path, final_pdf)
				os.remove(pdf_obj.pdf_local_path)
				pdf_obj.pdf_local_path = final_pdf # so that we can check again when we update the ead
			else:
				logr.error(final_pdf + ' exists, will not replace it.')
				logr.error('The new pdf may still be at ' + pdf_obj.pdf_local_path)
			
			# TIFF
			if not os.path.exists(final_tiff_dir):
				os.makedirs(final_tiff_dir, 0755)
				logr.info("Made " + final_tiff_dir)
				for f in os.listdir(pdf_obj.tiffs_dir):
					f = os.path.join(pdf_obj.tiffs_dir, f)
					copy(f, final_tiff_dir)
					os.remove(f)
				
				pdf_obj.tiffs_dir = final_tiff_dir # so that we can check again when we update the ead
				
			else:
				logr.error(final_tiff_dir + ' exists, will not replace or update it.')
				logr.error('The files may still be at ' + pdf_obj.tiffs_dir)
			
		


def _setup():
	# explicit
	global _XLINK_NS, _EAD_NS, _METS_NS
	
	# computed
	global _LIB, _BIN, _ETC, _ENV, SRGB_PROFILE, GRAY_PROFILE
	
	# read from conf
	global TIFFS_LOCAL_ROOT, TIFFS_FINAL_ROOT, PDFS_LOCAL_ROOT, PDFS_FINAL_ROOT
	global JP2S_ROOT, METS_ROOT, TMP_DIR, BITMAPS_ROOT
	global logr
	
	# utilities (also read from conf)
	global PDFIMAGES, CONVERT, PYTHON, JAVA

	_LIB = os.path.dirname(os.getcwd()) + "/lib"
	_BIN = os.path.dirname(os.getcwd()) + "/bin"
	_ETC = os.path.dirname(os.getcwd()) + "/etc"
	SRGB_PROFILE = _LIB + os.sep + 'sRGB.icc'
	GRAY_PROFILE = _LIB + os.sep + 'gray22.icc'
	
	_ENV = { "LD_LIBRARY_PATH":_LIB }

	_XLINK_NS = "http://www.w3.org/1999/xlink"
	_EAD_NS = "urn:isbn:1-931666-22-9"
	_METS_NS = "http://www.loc.gov/METS/"
	
	# Logging
	logging.config.fileConfig(_ETC + '/logging.conf')
	logr = logging.getLogger('main')
	
	# Main configuration
	conf = ConfigParser.RawConfigParser()
	conf.read(_ETC + '/main.conf')

	TIFFS_LOCAL_ROOT = conf.get('directories', 'tiffs_local_root')
	TIFFS_FINAL_ROOT = conf.get('directories', 'tiffs_final_root')
	
	PDFS_LOCAL_ROOT = conf.get('directories', 'pdfs_local_root')
	PDFS_FINAL_ROOT = conf.get('directories', 'pdfs_final_root')
	
	JP2S_ROOT = conf.get('directories', 'jp2s_final_root')
	
	METS_ROOT = conf.get('directories', 'mets_final_root')
	
	TMP_DIR = conf.get('directories', 'tmp')
	BITMAPS_ROOT = conf.get('directories', 'bitmaps_root')
	
	PDFIMAGES = conf.get('utilities', 'pdfimages')
	CONVERT = conf.get('utilities', 'convert')
	PYTHON = conf.get('utilities', 'python')
	JAVA = conf.get('utilities', 'java')
	
	if not os.path.exists(TMP_DIR):	os.makedirs(TMP_DIR)


if __name__ == '__main__':
	# ead = "/home/jstroop/workspace/pulfa1.0/eads/mudd/publicpolicy/MC216.EAD.xml"
	ead = argv[1]
	 
	_setup()

	report_path = os.path.join(TMP_DIR, "pdfs.txt")

	pdf_objects = get_pdfs(ead)
	
	# write these out so that we can stop and start.
	Pdf.serialize(report_path, pdf_objects)

	del pdf_objects[:] # clear the list

	logr.debug("-----------------------BITMAP EXTRACTION-----------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	for pdf in pdf_objects:
		logr.debug("---------------------------------------------------------------------------")
		extract_bitmaps_from_pdf(pdf)
	Pdf.serialize(report_path, pdf_objects)

	del pdf_objects[:] # clear the list
	
	logr.debug("-----------------------TIFF CONVERSION-------------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	for pdf in pdf_objects:
		logr.debug("---------------------------------------------------------------------------")
		bitmaps_to_tiff(pdf, rm_bitmaps=True) # False WHILE DUBUGGING
	Pdf.serialize(report_path, pdf_objects)

	del pdf_objects[:] # clear the list

	logr.debug("-----------------------JP2 CONVERSION--------------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	for pdf in pdf_objects:
		logr.debug("---------------------------------------------------------------------------")
		tiffs_to_jp2(pdf)
	Pdf.serialize(report_path, pdf_objects)
	
	del pdf_objects[:] # clear the list
	
	logr.debug("-----------------------METS------------------------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	for pdf in pdf_objects:
		logr.debug("---------------------------------------------------------------------------")
		pdf_obj_to_mets(pdf)
	Pdf.serialize(report_path, pdf_objects)

	del pdf_objects[:] # clear the list

	logr.debug("-----------------------FINALIZE FILES--------------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	finalize(pdf_objects)
	Pdf.serialize(report_path, pdf_objects)
	
	
	logr.debug("-----------------------REVISE EAD------------------------------------------")
	pdf_objects = Pdf.slurp(report_path)
	update_ead(ead, pdf_objects)


	exit(0)
