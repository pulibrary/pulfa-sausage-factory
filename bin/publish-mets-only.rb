#!/usr/bin/ruby

# README:
# This file takes a call number and iterates through the directories, generates mets, 
# and (eventually) inserts dao elements in EADs
# Do not use database for this.  Instead, take an argument that represents a collection directory.
# Example: ruby publish.rb C0022

require 'rubygems'
require 'parseconfig'
require 'nokogiri'

=begin
require "open4"
require 'logger'

# Log stdout and stderr
log = Logger.new("../log/pulfarize.log")
log.level = Logger::DEBUG
def execute(cmd, logger)
	logger.info cmd
	Open3.popen3(cmd) do |stdin, stdout, stderr|
		out = "#{stdout.read}"
		err = "#{stderr.read}"
		if(!err.empty?)
	    	logger.error "stderr - " + err
	    end
	    if(!out.empty?)
	    	logger.debug "stdout - " + out
	    end
	end
end
=end

begin
	# args
	callno = ARGV[0]
	fail "YOU FORGOT TO SPECIFY A CALL NUMBER TO PUBLISH!!!" unless callno

    # vars
	pufla_url = 'http://findingaids.princeton.edu/collections/'
        jp2_store = '/mnt/libimages/data/jp2s/'
        #jp2_store = '/mnt/libserv64/vol2/pudl/'
        # jp2_store = '/tmp/jp2s/'
	# tiff_store = '/mnt/libserv37/dps/'
	tiff_store = '/mnt/diglibdata/archives/'
	#tiff_store = '/usr/share/images/libserv64/vol4/'
	# tiff_store = '/tmp/tiffs/'
	_ETC = File.dirname(Dir.pwd) + '/etc'
	_LIB = File.dirname(Dir.pwd) + '/lib'
	conf = ParseConfig.new( _ETC + '/main.conf' )
	JAVA = conf['utilities']['java']
	TMP_DIR = conf['directories']['tmp']
	METS_PATH = conf['directories']['mets_final_root']
	EAD_PATH = conf['directories']['ead_root']


	# Start iterating...
	if(File.exists?(jp2_store + callno))
	    Dir.foreach(jp2_store + callno) {|component| 
	    
			if(!component.include?('.'))
			   component_id = callno + '/' + component
			    
			   if(File.exists?(jp2_store + component_id + '.pdf'))

				 component_url = pufla_url + component_id + '.xml'
                                 doc = `curl #{component_url}`
                                 component_xml = Nokogiri::HTML(doc)
				 unit_title_pre = component_xml.xpath('//c/did/unittitle').text + ': ' + component_xml.xpath('//c/did/unitdate').text
                                 unit_title = unit_title_pre.gsub(/"/, '')
			
			    
				# set up args for pre-mets
				output = jp2_store + component_id + '.xml'     
				#output = TMP_DIR + component_id + '.xml'
				input_jp2 = jp2_store + component_id
				input_tiff = tiff_store + component_id
				objid = component_id
				docid = 'http://findingaids.princeton.edu/folders/' + component_id + '.mets'
				
				# generate pre-mets
				premets_cmd = 'sudo ./dao.py --output ' + output + ' --input ' + input_jp2 +'.pdf --input ' + input_jp2 + ' --input ' + input_tiff + ' --objid ' + objid + ' --docid ' + docid
				puts premets_cmd
				system(premets_cmd)
					
					# xslt pre-mets to mets arguments
					saxon_cmd = JAVA + ' -jar ' + _LIB + '/saxon9he.jar ' 
					saxon_cmd = saxon_cmd + '-xsl:' + _LIB + '/folder2mets.xsl '
					saxon_cmd = saxon_cmd + '-s:' + output + ' -o:' + METS_PATH + '/' + component_id + '.mets '
					saxon_cmd = saxon_cmd + 'title="' + unit_title + '"'
					# logr.debug('saxon_cmd: ' + saxon_cmd)
					
					puts saxon_cmd
					#transform the xml file into a mets
					if(system(saxon_cmd))
						puts "\n\nTransformed: #{output}"
					else
						puts "\n\nUnable to transform: #{output}"
					end
				
			end
		     end
	    
	    }	
    else
    	puts 'Oops! A directory does not exist for that call number (' + callno + ') in ' + jp2_store
    end
end
