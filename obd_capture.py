#!/usr/bin/env python

import obd_io
import serial
import platform
import obd_sensors
import json
import socket    #&L Added socket library
import urllib2   #MJ Added url library (urllib) ---If Python 2.x use urllib2

from datetime import datetime
import time

from obd_utils import scanSerial

class OBD_Capture():
    def __init__(self):
        self.port = None
        self.soc = None #&L add socket as member
        localtime = time.localtime(time.time())

    def socConnect(self): #&L Added function to connect to host. We should probably change the port. Also, we should propbably add some error checking.
        HOST = '203.42.134.229'    # The remote host. Correct address.
        PORT = 50007              # The same port as used by the server
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.connect((HOST, PORT))    #JD Should be self.soc.connect()  ??  #&L Will fail if server does not accept. Might be worth trying on a local network.
        #JD I am pretty sure some sort of authentication will be needed here when connecting to the server ??

    def socIsConnected(self):
        return self.soc;

    def connect(self):
        portnames = scanSerial()
        print portnames
        for port in portnames:
            self.port = obd_io.OBDPort(port, None, 2, 2)
            if(self.port.State == 0):
                self.port.close()
                self.port = None
            else:
                break

        if(self.port):
            print "Connected to "+self.port.port.name
            
    def is_connected(self):
        return self.port
        
    def capture_data(self):

        #Find supported sensors - by getting PIDs from OBD
        # its a string of binary 01010101010101 
        # 1 means the sensor is supported
        self.supp = self.port.sensor(0)[1]
        self.supportedSensorList = []
        self.unsupportedSensorList = []

        # loop through PIDs binary
        for i in range(0, len(self.supp)):
            if self.supp[i] == "1":
                # store index of sensor and sensor object
                self.supportedSensorList.append([i+1, obd_sensors.SENSORS[i+1]])
            else:
                self.unsupportedSensorList.append([i+1, obd_sensors.SENSORS[i+1]])
        print "--- Supported OBDII PIDs ---"
		print "Index \t Name"
        for supportedSensor in self.supportedSensorList:
            print str(supportedSensor[0]) + "\t" + str(supportedSensor[1].shortname)        
        
        time.sleep(1)
        
        if(self.port is None):
            return None

        #Loop until Ctrl C is pressed        
        try:
            while True:
                json_data = []    #JD
                localtime = datetime.now()
                current_time = str(localtime.hour)+":"+str(localtime.minute)+":"+str(localtime.second)+"."+str(localtime.microsecond)
                json_data.append({'Time':current_time})    #JD
                results = {}
                for supportedSensor in self.supportedSensorList:
                    sensorIndex = supportedSensor[0]
                    (name, value, unit) = self.port.sensor(sensorIndex)
                    json_data.append({name + " ("+unit+")":value})    #JD   fixed str and list issue

                print "\n"+json.dumps(json_data)         #JD SEND THIS TO SERVER PERIODICALLY (Single packet of information)
                #self.soc.send(json.dumps(json_data))   #JD using mitch's code #&L Send to server.
                
                #Jacob------------------Authentication-----------------------                
                # Create an OpenerDirector with support for Basic HTTP Authentication...
                auth_handler = urllib2.HTTPBasicAuthHandler()
                auth_handler.add_password(realm='OBDII',
                                          uri='http://203.42.134.229/',
                                          user='adam',        #JD also tried user|passwd combination uow|m2muow
                                          passwd='adam')
                opener = urllib2.build_opener(auth_handler)
                # ...and install it globally so it can be used with urlopen.
                urllib2.install_opener(opener)
                #------------------------------------------------------------
                
                #------------------------Mitch's Code------------------------
                #Crease a http request, chuck in the correct address when adam gives us one
                request = urllib2.Request('http://203.42.134.229/')    #JD Added IP address, will assume saving to home directory
                #Assume that we have to do proper http, so add a header specifying that it's json
                request.add_header('Content-Type', 'application/json')
                #Send the request and attach the raw json data
                response = urllib2.urlopen(request,json.dumps(json_data))
                #----------------------------End-----------------------------
                
                time.sleep(0.5)                 #Should probably iterate a few times before sending json data

        except KeyboardInterrupt:
            self.port.close()
            print("stopped")

if __name__ == "__main__":

    o = OBD_Capture()
    o.connect()
    #o.socConnect()    #JD stub, using mitch's code #&L Added code to connect to server.
    time.sleep(1)
    if ( not o.is_connected() ): #&L Added check for socket; don't run if se
        print "Not connected to OBD Dongle"
    #elif ( not o.socIsConnected() ): #JD using mitch's code #JD Altered for more accurate debug
    #    print "Not connected to Server" #JD using mitch's code
    else:
        o.capture_data()