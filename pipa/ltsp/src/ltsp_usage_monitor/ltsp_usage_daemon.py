#!/usr/bin/python

import re
import datetime
import os
import sys
from glob import glob
import pwd
import socket
import logging
import md5
import daemon
import select
import signal
import stat
import threading
import time
import simplejson as json

### Settings

LTSP_HOME = '/home/ltsp'
HOST=''
PORT=31000
DAEMON_CONF = os.path.join(os.path.dirname(__file__), 'ltspstats.conf')
UNIX_SOCKET='/tmp/ltspstats'
POST_INTERVAL = 60
POST_URL = 'http://www.kiberpipa.org/services/ltsp/usage/'
LTSP_USAGE_SECRET = 'xxx'

M_AVG=6
M_THR=3

#### End Settings

# format: "Tue Nov 14 08:17:51 2006 uid: 1011 mousemoved: 0\n"
log_re = re.compile("^\w+\s(?P<month>\w+)\s(?P<day>\d+)\s(?P<hours>\d+)\W(?P<minutes>\d+)\W(?P<seconds>\d+)\s(?P<year>\d+)\suid\s(?P<uid>\d+)\s(mousemoved)\s(?P<mousemoved>\d)")
month = { 'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12,}


def handle_exit(signum, frame):
	print 'Signal received, stopping...'
	for t in threading.enumerate():
		if t.getName() != 'MainThread':
			t.keep_running = False
			t.join()
	sys.exit(1)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

def refresh():
	uname = pwd.getpwuid(int(m.groups()[7]))
	usage[uname.pw_name] = int(sum(term_list) > 3)

class PostingThread(threading.Thread):
	def __init__(self, statusdict):
		self.keep_running = True
		self.status = statusdict
		super(PostingThread, self).__init__()
	
	def run(self):
		import urllib
		
		while self.keep_running:
			time.sleep(POST_INTERVAL)
			
			s = self.status.copy()
			now = datetime.datetime.now() - datetime.timedelta(0, POST_INTERVAL)
			terminals = {}
			for k, v in s.iteritems():
				vals = [i[1] for i in v if i[0] >= now]
				if vals:
					if sum(vals) >= M_THR:
						terminals[k] = 1
					else:
						terminals[k] = 0
			
			data = json.dumps({'time': list(now.timetuple())[:7], 'count': sum(terminals.values())})
			
			post_args = {
				'data': data,
				'sign': md5.new(data + LTSP_USAGE_SECRET).hexdigest(),
				}
			
			args = urllib.urlencode(post_args)
			urllib.urlopen(POST_URL, args).read()

class TerminalStatsDaemon(daemon.Daemon):
	default_conf = DAEMON_CONF
	section = "ltspstats"
	socket = None
	
	def run(self):
		status = {}
		
		pt = PostingThread(status)
		pt.start()
		
		# cleanup unix socket
		if os.path.exists(UNIX_SOCKET):
			mode = os.stat(UNIX_SOCKET)[stat.ST_MODE]
			if stat.S_ISSOCK(mode):
				os.remove(UNIX_SOCKET)
		
		# bind unix socket
		try:
			usocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			usocket.bind(UNIX_SOCKET)
			usocket.listen(5)
		except socket.error, (value, message):
			if usocket:
				usocket.close()
			logging.info("Could not open local socket: " + message)
			sys.exit(1)
		
		os.chmod(UNIX_SOCKET, 666) # da lahko daemoni pisejo not.
		
		# main loop
		input = [usocket]
		output = []
		while 1:
			inputready,outputready,exceptready = select.select(input,output,[])
			for s in inputready:
				# sprejemanje unix povezav
				if s == usocket:
					uclient, address = usocket.accept()
					logging.info(address)
					input.append(uclient)
				# pobiranje podatkov
				else:
					data = s.recv(64)
					m = log_re.match(data)
					if m:
						d = m.groupdict()
						# tu se urejajo zbrane informacije
						uname = pwd.getpwuid(int(d['uid']))
						lst = status.get(uname.pw_name,[])
						
						lst.append((
							datetime.datetime(int(d['year']),int(month[d['month']]), int(d['day']),int(d['hours']),int(d['minutes']),int(d['seconds'])),
							int(d['mousemoved']),
							))
						if len(lst) > M_AVG:
							lst.pop(0)
						
						status[uname.pw_name] = lst
					
					s.close()
					input.remove(s)
			
			# posiljanje podatkov
			for s in outputready:
				s.send("")

if __name__ == "__main__":
	if "nodaemon" in sys.argv:
		TerminalStatsDaemon().run()
	else:
		TerminalStatsDaemon().main()
