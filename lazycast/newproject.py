#!/usr/bin/env python3
from subprocess import STDOUT, check_output
import socket
from time import sleep
import os
import uuid
import subprocess
import select
import traceback
import sys
import threading
import time
import datetime

commands = {}
commands[1] = 'SOURCE_READY'
commands[2] = 'STOP_PROJECTION'
commands[3] = 'SECURITY_HANDSHAKE'
commands[4] = 'SESSION_REQUEST'
commands[5] = 'PIN_CHALLENGE'
commands[6] = 'PIN_RESPONSE'

types = {}
types[0] = 'FRIENDLY_NAME'
types[2] = 'RTSP_PORT'
types[3] = 'SOURCE_ID'
types[4] = 'SECURITY_TOKEN'
types[5] = 'SECURITY_OPTIONS'
types[6] = 'PIN_CHALLENGE'
types[7] = 'PIN_RESPONSE_REASON'

if os.path.exists('uuid.txt'):
	uuidfile = open('uuid.txt','r')
	lines = uuidfile.readlines()
	uuidfile.close()
	uuidstr = lines[0]
else:
	uuidstr = str(uuid.uuid4()).upper()
	uuidfile = open('uuid.txt','w')
	uuidfile.write(uuidstr)
	uuidfile.close()


def avahi_service_is_running():
	process = subprocess.run(['avahi-browse', '-tp', '_display._tcp'], capture_output=True)
	return len(process.stdout) > 0
	

def publish_avahi_service(hostname, uuid):
	if not avahi_service_is_running():
		popen = subprocess.Popen(['avahi-publish-service', hostname, '_display._tcp', '7250', f'container_id={{{uuid}}}'], stdout=subprocess.PIPE)
	else:
		print('Avahi service is already running')

def check_rtp(port) : 
		file_name = f'/root/file_{port}'
		try : 
		#	process = subprocess.run(['tcpdump', '-U', '-i', 'eno1', '-s', '100', 'port', '7236'], capture_output=True, timeout=5)
		#	output = check_output('tcpdump -i eno1 -s 1500 port 7236', stderr=STDOUT, timeout=5)
			port_str = f'{port}'
			output = check_output(['sh', '/root/tcpscript.sh', port_str, file_name], stderr=STDOUT, timeout=7)
		except Exception as e:
			print (f'output :  exception {e}')

		b = os.path.getsize(file_name)
		print (f'size of the file is in bytes {b}')
		os.remove(file_name)
		os.system(f'pkill -f tcpdump.*port\ {port}')
		return b > 0
	

print ("project argv", sys.argv)
hostname = sys.argv[1]

publish_avahi_service(hostname, uuidstr)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('',7250))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.listen(1)

def run_session (conn, sourceip, port) : 
	start_time = datetime.datetime.now()
	while True:
		
		conn.settimeout(5)
		try : 
			data = conn.recv(1024)
		except Exception as e:
			print(f'recv timedout')
			if check_rtp(port) : 
				print ('stream is comming')
			else :
				print ('stream is stopped')
				print('Source is diconnecting...')
				os.system(f'pkill -f cvlc.*{port}')
				os.system(f'pkill -f miracle-sink.*-p\ {port}')
				break
			continue
			
		# print data
		print(data.hex())

		if len(data) == 0:
			break

		
		data = data.hex()
		size = int(data[0:4],16)
		version = int(data[4:6])
		command = int(data[6:8])

		print(size,version,command)
		
		messagetype = commands[command]
		print(messagetype)

		if messagetype == 'SOURCE_READY':
			print('Source is ready...')
			process = subprocess.run(['avahi-browse', '-tp', '_display._tcp'], capture_output=True)
			os.system(f'sudo /usr/bin/miracle-sinkctl -p {port} -s {sourceip} -e run-vlc.sh --log-level debug --log-journal-level debug -- set-friendly-name {hostname} &')
			#os.system('./d2.py '+sourceip+' &')

		if messagetype == 'STOP_PROJECTION':
			print('Source is diconnecting...')
			os.system(f'pkill -f cvlc.*{port}')
			os.system(f'pkill -f miracle-sink.*-p\ {port}')
			break
			
				

	end_time = datetime.datetime.now()
	f = open("/home/letsving/.screencast.log", 'a')	
	f.write(f"{start_time},{end_time},miracast\n")
	f.close();

	conn.close()


def main():
	port = 7236
	threads = []

	while True: 
		(conn, addr) = sock.accept()
		print('Connected by', addr)
		sourceip = addr[0]
		t1 = threading.Thread(target=run_session, args=(conn, sourceip, port,))
		port += 1
		t1.start()
		threads.append(t1)

	for thread in threads : 
		thread.join()

	sock.close()

try:
	main()
except Exception as e:
	print(e)
	print(traceback.format_exc())
	sock.close()
