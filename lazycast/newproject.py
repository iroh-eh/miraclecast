#!/usr/bin/env python3
"""
	This software is part of lazycast, a simple wireless display receiver for Raspberry Pi
	Copyright (C) 2020 Hsun-Wei Cho
	Using any part of the code in commercial products is prohibited.
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import socket
from time import sleep
import os
import uuid
import subprocess
import select
import traceback

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
	

hostname = 'lazyletsving'
publish_avahi_service(hostname, uuidstr)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('',7250))
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.listen(1)


def main():
	while True: 
		start_checking = False
		(conn, addr) = sock.accept()
		print('Connected by', addr)
		sourceip = addr[0]
		while True:
		
			print(f'came here with bool {start_checking}')
			conn.settimeout(5)
			try : 
				data = conn.recv(1024)
			except Exception as e:
				print(f'recv timedout')
				try : 
					for i in range(0, 20) : 
						x = conn.send(b'1101010101010101010101010101010101010100')
					print (f'this is x : {x}')
					rs, ws, _ = select.select([conn], [conn], [], 5)
					print (f'rs : {rs} ws : {ws}')
					if len(rs) == 0 or len(ws) == 0:
						print('Socket on source is dead...')
					continue
				except Exception as e:
					print (f'raise exception while sending the bytes')
					break
					
				
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
				os.system(f'sudo /usr/bin/miracle-sinkctl -s {sourceip} -e run-vlc.sh --log-level debug --log-journal-level debug -- set-friendly-name lazyletsving &')
				start_checking = True
				#os.system('./d2.py '+sourceip+' &')
		
			if messagetype == 'STOP_PROJECTION':
				print('Source is diconnecting...')
				os.system(f'sudo pkill miracle-sink')
				break
			
			if start_checking : 
				try:
					x = conn.send(b'0')
					print (f'this is x : {x}')

					#rtp_source_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

					#print('Attempting connection to sourceip:7236...')
					#rtp_source_sock.settimeout(10)
					#rtp_source_sock.connect((sourceip, 7236))
					#print('...connected to sourceip:7236')

					#rtp_source_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
					#rtp_source_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					#rs, ws, _ = select.select([rtp_source_sock], [rtp_source_sock], [], 5)
					#if len(rs) == 0 or len(ws) == 0:
					#	print('Socket on source is dead...')
				except Exception as e:
					print(e)
					print('Source is diconnecting...')
					os.system(f'sudo pkill miracle-sink')
					break
					print(traceback.format_exc())
			
			

		conn.close()
	sock.close()

try:
	main()
except Exception as e:
	print(e)
	print(traceback.format_exc())
	sock.close()
