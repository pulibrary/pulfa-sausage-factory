#!/usr/bin/ruby

require 'rubygems'
require 'sqlite3'
require 'parseconfig'
require "open3"
require 'logger'

# Note!  You need to run this script with rvmsudo.
# Example: rvmsudo ruby makepdf.rb
#

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

begin
    # vars
    # db_path = '/home/shaune/workspace/ib/ib.db'
    db_path = '/home/shaune/workspace/pulfa-image-harvester/mc180.db'
    
    SOURCE_ROOT="/usr/share/images/libserv37/dps/"
	DESTINATION_ROOT="/usr/share/images/libserv64/vol2/pudl/"
	
	db = SQLite3::Database.open db_path
	
	stm = db.prepare 'SELECT * FROM ImageDirs where Note=" "'
    rs  = stm.execute
    
    rs.each do |row|
		if row[1] =~ /http:\/\/findingaids\.princeton\.edu\/collections\/.*/
    		  component = row[1].sub( 'http://findingaids.princeton.edu/collections/', '')
		else 
		  component = row[1]
		end
		cmd = 'sudo sh ./dirtopdf.sh -d -s 3200 -o ' + DESTINATION_ROOT + component + '.pdf ' + SOURCE_ROOT + component 
		puts cmd
		execute(cmd, log)
		
	end

rescue SQLite3::Exception => e
    puts "There was an error:"
    puts e

ensure
	stm.close if stm
    db.close if db
end
