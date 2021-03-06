#!/usr/bin/env python
###########################################################################
# odb_io.py
# 
# Copyright 2004 Donour Sizemore (donour@uchicago.edu)
# Copyright 2009 Secons Ltd. (www.obdtester.com)
#
# This file is part of pyOBD.
#
# pyOBD is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pyOBD is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyOBD; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###########################################################################


#######################################################################################################
#            University of Wollongong (UOW) Telstra M2M Challenge Team                                #
#                                                                                                     #
# This code has been modified as part of the Telstra M2M University Challenge 2013                    #
# It's modifications are owned by the UOW Telstra M2M Team and is not to be redistributed for sale.   #
#                                                                                                     #
# Contact: jacob.donley089@uowmail.edu.au                                                             # 
# Contributions by: Jacob Donley, Luke Angove and Mitchell Just                                      #
#                                                                                                   #
# This header should be kept unmodified.                                                           #
###################################################################################################


import serial
import string
import time
import os
import sys
from math import ceil
#import #wx #due to debugEvent messaging

import obd_sensors

from obd_sensors import hex_to_int

GET_DTC_COMMAND   = "03"
CLEAR_DTC_COMMAND = "04"
GET_FREEZE_DTC_COMMAND = "07"

from debugEvent import *

#__________________________________________________________________________
def decrypt_dtc_code(code):
    """Returns the 5-digit DTC code from hex encoding"""
    dtc = ""
    print "decrypt_dtc_code_code " + code
    #if len(code)<4:
    #   os.popen('dbus-send --type=method_call --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.SystemNoteInfoprint string:"ERROR: Tried to decode bad DTC"')
    #   raise "Tried to decode bad DTC: %s" % code

    tc = obd_sensors.hex_to_int(code[0]) #typecode
    tc = tc >> 2
    if   tc == 0:
        type = "P"
    elif tc == 1:
        type = "C"
    elif tc == 2:
        type = "B"
    elif tc == 3:
        type = "U"
    else:
        os.popen('dbus-send --type=method_call --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.SystemNoteInfoprint string:"ERROR!"')
        raise tc

    dig1 = str(obd_sensors.hex_to_int(code[0]) & 3)
    dig2 = str(obd_sensors.hex_to_int(code[1]))
    dig3 = str(obd_sensors.hex_to_int(code[2]))
    dig4 = str(obd_sensors.hex_to_int(code[3]))

    dtc = type+dig1+dig2+dig3+dig4
    return dtc
#__________________________________________________________________________

class OBDPort:
     """ OBDPort abstracts all communication with OBD-II device."""
     def __init__(self,portnum,_notify_window,SERTIMEOUT,RECONNATTEMPTS):
         """Initializes port by resetting device and gettings supported PIDs. """
         # These should really be set by the user.
         baud     = 9600
         databits = 8
         par      = serial.PARITY_NONE  # parity
         sb       = 1                   # stop bits
         to       = SERTIMEOUT
         self.ELMver = "Unknown"
         self.State = 1 #state SERIAL is 1 connected, 0 disconnected (connection failed)
         #print self.State
         self._notify_window=_notify_window
         #wx.PostEvent(self._notify_window, DebugEvent([1,"Opening interface (serial port)"]))                

         try:
             self.port = serial.Serial(portnum,baud, \
             parity = par, stopbits = sb, bytesize = databits,timeout = to)
             
         except serial.SerialException:
             self.State = 0
             return None
             
         #wx.PostEvent(self._notify_window, DebugEvent([1,"Interface successfully " + self.port.portstr + " opened"]))
         #wx.PostEvent(self._notify_window, DebugEvent([1,"Connecting to ECU..."]))
         #print self.State
         count=0
         while 1: #until error is returned try to connect
             try:

                self.send_command("atz")   # initialize
                time.sleep(0.2)
                
             except serial.SerialException:
                self.State = 0
#mmmm                
             response1=self.get_result()
             print "1st Response: "+response1
             if response1=="atz":
                    response2=self.get_result()
                    print "2nd Response: "+response2
                    self.ELMver = response2
             else:
                    self.ELMver = response1

             #wx.PostEvent(self._notify_window, DebugEvent([2,"atz response:" + self.ELMver]))
             #print "self.state: "+str(self.State)

             self.send_command("ate0")  # echo off
             time.sleep(0.2)
             #print self.get_result()
             #wx.PostEvent(self._notify_window, DebugEvent([2,"ate0 response:" + self.get_result()]))

             self.send_command("at sp 0") # Set automatic protocol search mode 
             time.sleep(0.3)
             answ=self.get_result()
             print "Connection: " + answ
             #wx.PostEvent(self._notify_window, DebugEvent([2,"atsp0 response:" + answ]))

             self.send_command("0100")
             time.sleep(0.3)
             ready = self.get_result()
             print "Supported PIDs: "+ready
             time.sleep(0.5)
             #wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response1:" + ready]))

#UNABLE TO CONNECT
#SEARCHING...            

             if ready=="SEARCHING...":
                time.sleep(1.5)
                ready = self.get_result()
                time.sleep(0.3)

             if ready=="BUS INIT: OK":
                #ready=self.get_result()
                print "Supported PIDs: "+ready
                #wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response2:" + ready]))
                return None

             elif ready=="BUSINIT: ...OK":
                #ready=self.get_result()
                print "Supported PIDs: "+ready
                #wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response2:" + ready]))
                return None
            
             elif ready[:2]=="41":
                print "Supported PIDs: "+ready
                #wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response2:" + ready]))
                return None

             else:             
                #ready=ready[-5:] #Expecting error message: BUSINIT:.ERROR (parse last 5 chars)
                #wx.PostEvent(self._notify_window, DebugEvent([2,"Connection attempt failed:" + ready]))
                time.sleep(3.5)
                if count==RECONNATTEMPTS:
                  self.close()
                  self.State = 0
                  return None
                #wx.PostEvent(self._notify_window, DebugEvent([2,"Connection attempt:" + str(count)]))
                count=count+1          

              
     def close(self):
         """ Resets device and closes all associated filehandles"""
         
         if (self.port!= None) and self.State==1:
            self.send_command("atz")
            time.sleep(0.1)
            self.port.close()
         
         self.port = None
         self.ELMver = "Unknown"

     def send_command(self, cmd):
         """Internal use only: not a public interface"""
         if self.port:
             time.sleep(0.08)
             self.port.flushOutput()
             self.port.flushInput()
             time.sleep(0.05)
             for c in cmd:
                 self.port.write(c)
                 time.sleep(0.01)
             self.port.write("\r\n")
             time.sleep(0.05)
             #wx.PostEvent(self._notify_window, DebugEvent([3,"Send command:" + cmd]))
             #print "Send: " + cmd

     def interpret_result(self,code):
         """Internal use only: not a public interface"""
         # Code will be the string returned from the device.
         # It should look something like this:
         # '41 11 0 0\r\r'
         
         # 9 seems to be the length of the shortest valid response
         if len(code) < 7:
             print "Unrecognised Response"
             os.popen('dbus-send --type=method_call --dest=org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications.SystemNoteInfoprint string:"ERROR: BogusCode"')
             time.sleep(0.5)
             #raise "BogusCode"
             exit
         
         # get the first thing returned, echo should be off
         code = string.split(code, "\r")
         code = code[0]
         
         #remove whitespace
         code = string.split(code)
         code = string.join(code, "")
         
         #cables can behave differently 
         #print "CODE: " + code
         if code[:6] == "NODATA": # there is no such sensor
             return "NODATA"
         if code[:7] == "STOPPED": # BUSY
             return "NODATA"

             
         # first 4 characters are code from ELM
         code = code[4:]
         return code
    
     def get_result(self):
         """Internal use only: not a public interface"""
         #time.sleep(0.1) #JD. This may need changing to make more reliable commuincation over wireless protocols such as bluetooth. Possibly even removed.
         if self.port:
             buffer = ""
             while 1:
                 c = self.port.read(1)
                 if (c in ['\r', '\n']) and len(buffer) > 0:
                     break
                 else:
                     if c != "" and c != ">" and c != "?" and not (c in ['\r', '\n']):
                         buffer = buffer + c             
             #wx.PostEvent(self._notify_window, DebugEvent([3,"Get result:" + buffer]))
             return buffer
         #else:
            #wx.PostEvent(self._notify_window, DebugEvent([3,"NO self.port!" + buffer]))
         return None

     # get sensor value from command
     def get_sensor_value(self,sensor):
         """Internal use only: not a public interface"""

         cmd = sensor.cmd
         self.send_command(cmd)
         data = self.get_result()
         sys.stdout.write('+')
         sys.stdout.flush()
         #print "data: "+data
         
         if data:
             data = self.interpret_result(data)
             if data != str("NODATA") and data != str("STOPPED"):
                 data = sensor.value(data)

         else:
             return "NORESPONSE"
         return data

     # return string of sensor name and value from sensor index
     def sensor(self , sensor_index):

         """Returns 3-tuple of given sensors. 3-tuple consists of
         (Sensor Name (string), Sensor Value (string), Sensor Unit (string) ) """
         sensor = obd_sensors.SENSORS[sensor_index]
         r = self.get_sensor_value(sensor)
         return (sensor.shortname,r, sensor.unit)#1, sensor.unit2)

     def sensor_names(self):
         """Internal use only: not a public interface"""
         names = []
         for s in obd_sensors.SENSORS:
             names.append(s.name)
         return names
         
     def get_tests_MIL(self):
         statusText=["Unsupported","Supported - Completed","Unsupported","Supported - Incompleted"]
         
         statusRes = self.sensor(1)[1] #GET values

         statusTrans = [] #translate values to text
         
         statusTrans.append(str(statusRes[0])) #DTCs
         if str(statusRes) == "NODATA":
            print "NODATA or BUSY"
            return statusTrans
         
         if statusRes[1]==0: #MIL
            statusTrans.append("Off")
         else:
            statusTrans.append("On")
         for i in range(2,len(statusRes)): #Tests
              statusTrans.append(statusText[statusRes[i]]) 
         
         return statusTrans
          
     #
     # fixme: j1979 specifies that the program should poll until the number
     # of returned DTCs matches the number indicated by a call to PID 01
     #
     def get_dtc(self):
          print "get_dtc"
          """Returns a list of all pending DTC codes. Each element consists of
          a 2-tuple: (DTC code (string), Code description (string) )"""
          dtcLetters = ["P", "C", "B", "U"]
          r = self.sensor(1)[1] #data
          dtcNumber = r[0]
          mil = r[1]
          DTCCodes = []
          
          
          print "Number of stored DTC:" + str(dtcNumber) + " MIL: " + str(mil)
          # get all DTC, 3 per mesg response
          for i in range(0, ((dtcNumber+2)/3)):
            self.send_command(GET_DTC_COMMAND)
            res = self.get_result()
            print "DTC result:" + res
            for i in range(0, 3):
                DTC_raw = res[3+i*6:5+i*6] + res[6+i*6:8+i*6]
                if DTC_raw=="0000": #skip fill of last packet
                  break
                  
                DTCStr = decrypt_dtc_code(DTC_raw)
                DTCCodes.append(["Active",DTCStr])
          
          #read mode 7
          self.send_command(GET_FREEZE_DTC_COMMAND)
          res = self.get_result()
          
          if res[:7] == "NO DATA": #no freeze frame
            return DTCCodes
          
          print "DTC freeze result:" + res

          a=len(res)
          print "len(res): " + str(a)
          if a>9:

             for i in range(0, 3):
                 DTC_raw = res[3+i*6:5+i*6] + res[6+i*6:8+i*6]
                 if DTC_raw=="0000": #skip fill of last packet
                   break
                  
                 DTCStr = decrypt_dtc_code(DTC_raw)

                 #M se restituisce codici a 6 cifre invece che ha 5
                 if len(DTCStr)>5:
                    DTCStr = DTCStr[0]+DTCStr[2:]
                    print "DTCStr "+DTCStr

                 DTCCodes.append(["Passive",DTCStr])

          else:
              
             for i in range(0, 3):
                 val1 = hex_to_int(res[3+i*6:5+i*6])
                 val2 = hex_to_int(res[6+i*6:8+i*6]) #get DTC codes from response (3 DTC each 2 bytes)
                 val  = (val1<<8)+val2 #DTC val as int
                
                 if val==0: #skip fill of last packet
                   break
                   
                 DTCStr=dtcLetters[(val&0xC000)>14]+str((val&0x3000)>>12)+str(val&0x0fff)

                 #M se restituisce codici a 6 cifre invece che ha 5
                 if len(DTCStr)>5:
                    DTCStr = DTCStr[0]+DTCStr[2:]
                    print "DTCStr "+DTCStr

                 DTCCodes.append(["Passive",DTCStr])




          return DTCCodes
              
     def clear_dtc(self):
         print "def clear_dtc"
         """Clears all DTCs and freeze frame data"""
         self.send_command(CLEAR_DTC_COMMAND)     
         r = self.get_result()
         return r
     
     def log(self, sensor_index, filename): 
          file = open(filename, "w")
          start_time = time.time() 
          if file:
               data = self.sensor(sensor_index)
               file.write("%s     \t%s(%s)\n" % \
                         ("Time", string.strip(data[0]), data[2])) 
               while 1:
                    now = time.time()
                    data = self.sensor(sensor_index)
                    line = "%.6f,\t%s\n" % (now - start_time, data[1])
                    file.write(line)
                    file.flush()
          
