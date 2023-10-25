#!/usr/bin/env python3

import dbus
import sys, os
import time
from gi.repository import GLib as gobject
import threading
import socket
from dbus.mainloop.glib import DBusGMainLoop
from time import sleep
from threading import Event



##################### Settings #####################
#hostname = socket.gethostname() 
print (sys.argv)
hostname = sys.argv[1]
# If ./mice.py and ./project.py do not run on the same machine, 
# hostname and ipstr should be the those of the machine running ./project.py
ipstr = ''
# ipstr = '192.168.1.5'
concurrent = 0
# 0: Accept MICE connection only
# 1: Accept MICE and wifi p2p connections

event = Event()
ippipe = os.popen('hostname -I')
ipstrs = ippipe.read()
ippipe.close()
ipstrs = ipstrs[:ipstrs.find(' \n')]
ipelems = ipstrs.split(' ')
if len(ipelems)>1 and ipstr == '':
	print('Warning:')
	print('This machine has multiple IP addresses:')
	for ipelem in ipelems:
		print(ipelem)
	ipstr = ipelems[0]
	print('A PC will try to connect to '+ipstr+' directly if mDNS fails')
	print('Set the variable "ipstr" in mice.py to another IP manually if '+ipstr+' does not work')


def groupStarted(properties):

	print("groupStarted: " + str(properties))
	g_obj = dbus.SystemBus().get_object('fi.w1.wpa_supplicant1',properties['group_object'])
	res = g_obj.GetAll('fi.w1.wpa_supplicant1.Group', dbus_interface=dbus.PROPERTIES_IFACE, byte_arrays=True)
	print("Group properties: " + str(res))
	
	hostnamehex = hostname.encode('utf-8').hex()
	hostnamemessage = '2002'+'{:04X}'.format(int(len(hostname)))+hostnamehex

	ipmessage = ''
	
	if ipstr != '':
		# The spec supportes multiple ip attributes. However, Windows will only try the first one
		iphex = ipstr.encode('utf-8').hex()
		ipmessage = '2005'+'{:04X}'.format(int(len(iphex)/2))+iphex

	capandhostmessage = '0001372001000105' + hostnamemessage + ipmessage

	innerarray = []
	print(capandhostmessage)
	for c in bytes.fromhex(capandhostmessage):
		innerarray.append(dbus.Byte(c))

	g_obj.Set('fi.w1.wpa_supplicant1.Group', 'WPSVendorExtensions',  
	dbus.Array([dbus.Array(innerarray, signature=dbus.Signature('ay'))], signature=dbus.Signature('ay')),dbus_interface=dbus.PROPERTIES_IFACE)

	g_obj = dbus.SystemBus().get_object('fi.w1.wpa_supplicant1',properties['group_object'])
	res = g_obj.GetAll('fi.w1.wpa_supplicant1.Group', dbus_interface=dbus.PROPERTIES_IFACE, byte_arrays=True)
	print("Group properties: " + str(res))

	event.set()
	




def WpsFailure(status, etc):
	print("WPS Authentication Failure".format(status))
	print(etc)
	os._exit(0)

class P2P_Group_Add (threading.Thread):
	# Needed Variables
	global bus
	global wpas_object
	global interface_object
	global interfacep2pdevice
	global interface_name
	global wpas
	global wpas_dbus_interface
	global path

	# Dbus Paths
	global wpas_dbus_opath
	global wpas_dbus_interfaces_opath
	global wpas_dbus_interfaces_interface
	global wpas_dbus_interfaces_p2pdevice


	# Constructor
	def __init__(self,interface_name,wpas_dbus_interface):
		# Initializes variables and threads
		self.interface_name = interface_name
		self.wpas_dbus_interface = wpas_dbus_interface
		

		# Initializes thread and daemon allows for ctrl-c kill
		threading.Thread.__init__(self)
		self.daemon = True

		# Generating interface/object paths
		self.wpas_dbus_opath = "/" + self.wpas_dbus_interface.replace(".","/")
		self.wpas_wpas_dbus_interfaces_opath = self.wpas_dbus_opath + "/Interfaces"
		self.wpas_dbus_interfaces_interface = self.wpas_dbus_interface + ".Interface"
		self.wpas_dbus_interfaces_p2pdevice = self.wpas_dbus_interfaces_interface + ".P2PDevice"

		# Getting interfaces and objects
		DBusGMainLoop(set_as_default=True)
		self.bus = dbus.SystemBus()
		self.wpas_object = self.bus.get_object(self.wpas_dbus_interface, self.wpas_dbus_opath)
		self.wpas = dbus.Interface(self.wpas_object, self.wpas_dbus_interface)

		# Try to see if supplicant knows about interface
		# If not, throw an exception
		try:
			self.path = self.wpas.GetInterface(self.interface_name)
		except dbus.DBusException as exc:
			error = 'Error:\n  Interface ' + self.interface_name + ' was not found'
			print(error)
			usage()
			os._exit(0)

		self.interface_object = self.bus.get_object(self.wpas_dbus_interface, self.path)
		self.interfacep2pdevice = dbus.Interface(self.interface_object, self.wpas_dbus_interfaces_p2pdevice)

		self.bus.add_signal_receiver(groupStarted, dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
			signal_name="GroupStarted")
		self.bus.add_signal_receiver(WpsFailure, dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
			signal_name="WpsFailed")


	def setarguments(self):

		props = self.interface_object.GetAll(self.wpas_dbus_interfaces_p2pdevice,dbus_interface=dbus.PROPERTIES_IFACE)
		print(props)
		print('')	

		dbus.Interface(self.interface_object, dbus_interface=dbus.PROPERTIES_IFACE).Set(self.wpas_dbus_interfaces_p2pdevice, 'P2PDeviceConfig',dbus.Dictionary({ 'DeviceName' : hostname},signature='sv'))

		dbus.Interface(self.interface_object, dbus_interface=dbus.PROPERTIES_IFACE).Set(self.wpas_dbus_interfaces_p2pdevice, 'P2PDeviceConfig',dbus.Dictionary({dbus.String(u'PrimaryDeviceType'): dbus.Array([dbus.Byte(0), dbus.Byte(7), dbus.Byte(0), dbus.Byte(80), dbus.Byte(242), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0)])},signature='sv'))

		dbus.Interface(self.wpas_object, dbus_interface=dbus.PROPERTIES_IFACE).Set('fi.w1.wpa_supplicant1', dbus.String(u'WFDIEs'), dbus.Array([dbus.Byte(0), dbus.Byte(0), dbus.Byte(6), dbus.Byte(1), dbus.Byte(17), dbus.Byte(2), dbus.Byte(42), dbus.Byte(1), dbus.Byte(44), dbus.Byte(1), dbus.Byte(0), dbus.Byte(6), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(6), dbus.Byte(0), dbus.Byte(7), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0)], signature=dbus.Signature('y'), variant_level=1))
		#dbus.Interface(self.wpas_object, dbus_interface=dbus.PROPERTIES_IFACE).Set('fi.w1.wpa_supplicant1', dbus.String(u'WFDIEs'), dbus.Array([dbus.Byte(0), dbus.Byte(0), dbus.Byte(6), dbus.Byte(0), dbus.Byte(145), dbus.Byte(28), dbus.Byte(68), dbus.Byte(0), dbus.Byte(200)], signature=dbus.Signature('y'), variant_level=1))

		props = self.wpas_object.GetAll('fi.w1.wpa_supplicant1',dbus_interface=dbus.PROPERTIES_IFACE)
		print(props)
		print('')	

	def run(self):

		groupadddict = {'persistent':False}
		try:
			self.interfacep2pdevice.GroupAdd(groupadddict)
		except:
			print('Warning:\n  Could not preform group add')
			print('If existing beacon does not function properly, run ./removep2p.sh first.')
			print('Now running ./project.py')
			event.set()

		gobject.MainLoop().get_context().iteration(True)
		gobject.MainLoop().run()

if __name__ == "__main__":

	try:
		p2p_group_add_test = P2P_Group_Add('wlp0s20f3','fi.w1.wpa_supplicant1')
	except:
		print("Error:\n  Invalid Arguements")

	p2p_group_add_test.setarguments()
	p2p_group_add_test.start()


	event.wait()

	if concurrent == 1:
		os.system('./all.sh &')

	cmd = 'sudo python3 /root/newproject.py ' + '\'' + hostname + '\'';
	print (f'cmd {cmd}')
	os.system(cmd)

