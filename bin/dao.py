#!/usr/bin/env python
#-*-coding: utf-8-*-
import libxml2
import pyexiv2
import os
import hashlib
from datetime import datetime
from argparse import ArgumentParser

DEBUG = False # dumps data with labels to stdout.

def _hashfile(afile, hasher, blocksize=65536):
	buf = afile.read(blocksize)
	while len(buf) > 0:
		hasher.update(buf)
		buf = afile.read(blocksize)
	return hasher.hexdigest()

def currentDateTime():
	return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ%z")

class Representation(object):
	"""
	The objid is in the path, we use it to help us spilt the path into 
	local and cannonical parts and tell us if this represents the whole
	object or a part of it, e.g. 
	
	if:
	objid = AC044/c0002 and
	path = /home/jstroop/pulfa-img-harvest/output/jp2/AC044/c0002/00000001.jp2
	
	then:
	local = /home/jstroop/pulfa-img-harvest/output/jp2
	
	cannonical = AC044/c0002/00000001.jp2
	abs_name= AC044/c0002/00000001
	wholepart = part 
		
	Also takes care of checksums, calcuation of file size, 
	mime-type, dimensions, rights, use, etc.
	"""
	def __init__(self, objid, path):

		self.path = path

		_tokens = path.split("/" + objid)
		_local = _tokens[0]
		_file_name = _tokens[1]
		
		self.wholepart = ""
		if _file_name[0] == ".": self.wholepart = "whole"
		else: self.wholepart = "part"
		
		_file_name_no_ext = _file_name.split(".")[0]
		
		self.cannonical = objid + _file_name
		self.abs_name = objid + _file_name_no_ext

		# stuff calculated by _populateFields
		self.use = None
		self.checksumtype = "SHA-1"
		self.checksum = None
		self.size = None
		self.mimetype = None
		self.width = None
		self.height = None
		self.urn = None

		if DEBUG == True:
			os.sys.stdout.write(os.linesep + self.path + os.linesep)

		self._populateFields()

	def _populateFields(self):

		# use
		if self.path.endswith(".tif"):
			self.use = "master"
		else:
			self.use = "deliverable"

		#urn
		self.urn = "urn:pudl:images:" + self.use + ":" + self.cannonical

		#checksum
		self.checksum = _hashfile(file(self.path, "r"), hashlib.sha1())

		# size
		self.size = str(os.stat(self.path).st_size)

		if not self.path.endswith(".pdf"):
			#mime, width, height			
			metadata = pyexiv2.ImageMetadata(self.path)
			metadata.read()

			self.width = str(metadata.dimensions[0])
			self.height = str(metadata.dimensions[1])
			self.mimetype = metadata.mime_type
			
		if self.path.endswith(".pdf"): self.mimetype = "application/pdf"

		if DEBUG == True:
			os.sys.stdout.write("USE: " + self.use + os.linesep)
			os.sys.stdout.write("URN: " + self.urn + os.linesep)
			os.sys.stdout.write(self.checksumtype + ": ")
			os.sys.stdout.write(self.checksum + os.linesep)
			os.sys.stdout.write("SIZE: " + str(self.size) + os.linesep)
			os.sys.stdout.write("WIDTH: " + str(self.width) + os.linesep)
			os.sys.stdout.write("HEIGHT: " + str(self.height) + os.linesep)
			os.sys.stdout.write("MIMETYPE: " + str(self.mimetype) + os.linesep)

	def toElement(self):
		representationE = libxml2.newNode("representation")
		representationE.setProp("urn", self.urn)
		
		useE = libxml2.newNode("use")
		useE.setContent(self.use)
		representationE.addChild(useE)
		
		checksumE = libxml2.newNode("checksum")
		checksumE.setContent(self.checksum)
		checksumE.setProp("type", self.checksumtype)
		representationE.addChild(checksumE)
		
		sizeE = libxml2.newNode("size")
		sizeE.setContent(self.size)
		representationE.addChild(sizeE)
		
		mimetypeE = libxml2.newNode("mimetype")
		mimetypeE.setContent(self.mimetype)
		representationE.addChild(mimetypeE)
		
		if self.width:
			widthE = libxml2.newNode("width")
			widthE.setContent(self.width)
			representationE.addChild(widthE)
			
		if self.height:		
			heightE = libxml2.newNode("height")
			heightE.setContent(self.height)
			representationE.addChild(heightE)

		return representationE

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("--output", required=True, dest="out_name")
	parser.add_argument("--input", required=True, dest="input_nodes", action="append")
	parser.add_argument("--objid", required=True, dest="objid")
	parser.add_argument("--docid", required=True, dest="docid")
	
	args = parser.parse_args()
	docid = args.docid
	out_name = args.out_name
	objid = args.objid
	input_nodes = args.input_nodes
	
	# First create a list of Representation objects. These basically encapsulate
	# any path hacking and data extraction / calculation we have to do
	representations = []
	for node in input_nodes:
		if os.path.isfile(node):
			representations.append(Representation(objid, node))
		else: # isdir
			for f in os.listdir(node):
				path = node + os.sep + f
				representations.append(Representation(objid, path))
	
	
	# Now create a dict that uses the 'abstract pathnames' 
	# (e.g. ACO44/c0002/00000001) as keys, and has a list of Representation that 
	# represent it as the value.
	fGroups = {}
	for ctxt in representations:
		if ctxt.abs_name in fGroups:
			fGroups.get(ctxt.abs_name).append(ctxt)
		else:
			fGroups[ctxt.abs_name] = [ctxt]

	# We then serialize very simple XML (that can be turned into METS or 
	# anything else).
	doc = libxml2.newDoc("1.0")
	folderE = libxml2.newNode("folder")
	folderE.setProp("objid", objid)
	folderE.setProp("docid", docid)
	folderE.setProp("created", currentDateTime())
	doc.setRootElement(folderE)

	for k in sorted(fGroups.keys()):

		fGroup = fGroups.get(k)

		if fGroup[0].wholepart == "whole":
			for rep in fGroup:
				folderE.addChild(rep.toElement())

		if fGroup[0].wholepart == "part":
			memberE = libxml2.newNode("member")
			folderE.addChild(memberE)
			for rep in fGroup:
				memberE.setProp("abs_name", k)
				memberE.addChild(rep.toElement())				

	doc.saveFormatFileEnc(out_name, "UTF-8", 1)
	doc.freeDoc()
	
	os.sys.exit(0)
