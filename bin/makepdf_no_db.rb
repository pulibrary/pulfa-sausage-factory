#!/usr/bin/ruby

require 'rubygems'
require 'parseconfig'
require "open4"
require 'logger'

# Note!  You need to run this script with rvmsudo.
# Example: rvmsudo ruby makepdf.rb
#

# Log stdout and stderr
log = Logger.new("../log/pulfarize.log")
log.level = Logger::DEBUG

def execute(cmd, logger)
	logger.info cmd
	Open4.popen4(cmd) do |stdin, stdout, stderr|
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

begin
        # args
        callno = ARGV[0]
        fail "YOU FORGOT TO SPECIFY A CALL NUMBER TO PUBLISH!!!" unless callno

    # vars
        pufla_url = 'http://findingaids.princeton.edu/collections/'
        jp2_store = '/mnt/libserv64/vol2/pudl/'
    # jp2_store = '/tmp/jp2s/'
        # tiff_store = '/mnt/libserv37/dps/'
        tiff_store = '/mnt/libserv64/vol4/'
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
                		cmd = 'sudo sh ./dirtopdf.sh -d -s 3200 -o ' + jp2_store + component_id + '.pdf ' + tiff_store + component_id
                		puts cmd
                		system(cmd)
			end
		
		}
	end
end
