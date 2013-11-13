#!/usr/bin/ruby

require 'rubygems'
require 'sqlite3'
require 'parseconfig'
require "open3"
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


def move_images(img_store, row, img_ext, log)
	component = row[1].sub( 'http://findingaids.princeton.edu/collections/', '')
	chunks = component.split('/')
	
	# check to see if parent directory already exists... if not, create
	if(!File.exists?(img_store + chunks[0]))
		par_cmd = 'sudo mkdir ' + img_store + chunks[0]
    	if (execute(par_cmd, log))
    		puts 'Created directory:'
		else
			puts 'Unable to create directory:'
		end
	else
		log.info img_store + chunks[0] + ' directory already exists.'
	end

	# check to see if child dir already exists ... if not, create
	if(!File.exists?(img_store + component))
    	cmd = 'sudo mkdir ' + img_store + component
    	if (execute(cmd, log))
    		puts "Created directory: "
		else
			puts 'Unable to create directory: '
		end
	else
		log.info img_store + component + ' directory already exists.'
	end
	
	
	# before moving files to proper directory...
	# rename files based on current number of files in the directory and make sure files are listed in order
	
	new_loc = []
	Dir.foreach(img_store + component) {|y| 
		if(y.include?(img_ext))
			new_loc << y
		end
	}
	
	# how many image files already exist in the new location? Need to know where to start counting...
	total_files = new_loc.size
	next_file = total_files + 1
	
	# copy files one by one and rename accordingly
	Dir.foreach(img_store + row[0]) {|x| 
	    if(x.include?(img_ext))
			mv_cmd = 'sudo mv ' + 	img_store + row[0] + '/' + x + ' ' + img_store + component + '/' + sprintf("%08d", next_file) + img_ext
			execute(mv_cmd, log) 
			next_file = next_file + 1
		end
	}
end 

begin
    # vars
    db_path = '/home/shaune/workspace/ib/ib.db'
    jp2_store = '/usr/share/images/libserv64/vol2/pudl/'
    # jp2_store = '/tmp/jp2s/'
	tiff_store = '/usr/share/images/libserv37/dps/'
	# tiff_store = '/tmp/tiffs/'
	_ETC = File.dirname(Dir.pwd) + '/etc'
	_LIB = File.dirname(Dir.pwd) + '/lib'
	conf = ParseConfig.new( _ETC + '/main.conf' )
	JAVA = conf['utilities']['java']
	TMP_DIR = conf['directories']['tmp']
	METS_PATH = conf['directories']['mets_final_root']
	
	db = SQLite3::Database.open db_path
	
	stm = db.prepare 'SELECT * FROM ImageDirs where Note=""'
    rs  = stm.execute
    
    rs.each do |row|
		move_images(jp2_store, row, '.jp2', log)
		move_images(tiff_store, row,'.tif', log)
	end

rescue SQLite3::Exception => e
    puts "There was an error:"
    puts e

ensure
	stm.close if stm
    db.close if db
end