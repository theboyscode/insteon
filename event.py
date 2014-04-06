from log_str import *
from astral import Astral
from values import *
import time
import datetime
from time import localtime, strftime
import binascii
#setup the astral city, uses the city name fro values.py
a = Astral()
a.solar_depression = 'civil'
CITY = a[CITY_NAME]

class Event():
    def __init__(self, device, action,time, day_of_week, protocol,percent):
        self.device = device
        self.action  = action
        self.time = time
        self.day_of_week = day_of_week
        self.level = self.percent_to_level(percent)
        self.day_of_week_num = self.day_of_week2num(self.day_of_week)
        log_str('day of week = %s' % (self.day_of_week))
        self.protocol = protocol
        log_str('self.protocol = %s' % self.protocol)

    def get_command(self):
        return self.create_command()

    def get_command_time(self):
        now = localtime()
        sun = CITY.sun(date=datetime.date.today() + datetime.timedelta(days=self.day_of_week_num), local=True)
        if ((self.time == 'dawn') or (self.time == 'dusk')):
            #on below line need to account for the day offset
            time = str('%i:%i' % (sun[self.time].hour , sun[self.time].minute))
            log_str('%s is %s' % (self.time, time))
        else:
            time = self.time
        return self.event_time_to_week_secs(self.day_of_week_num,time)
        
    def percent_to_level(self,percent):
        level = hex(int(percent)*255/100)
        level = level[2:]
        level = level.upper()
        return level
        
    def create_command(self):
        if self.protocol == 'X10':
            return self.create_X10_command()
        elif self.protocol  == 'Insteon':
            return self.create_insteon_command()
        else:
            log_str("Command protocol does not match")
                
    def create_insteon_command(self):
        #need to figure out how to get this the address
        options = {'On':'0F 11 FF',
                   'Off':'0F 13 FF',
                   'none':'0F',
                   'Ramp':'0F 11'}
        
        if (self.action == 'Ramp'):
            command  = '02 62 %s %s %s' % (DEVICES[self.device],  options[self.action], self.level)
        elif (self.action == 'On'):
            command  = '02 62 %s %s' % (DEVICES[self.device],  options[self.action])
        elif (self.action == 'Off'):
            log_str("the command is: %s" % self.action )
            command  = '02 62 %s %s' % (DEVICES[self.device],  options[self.action])
        else:
            log_str("didn't get a correction action")
            
        log_str("Created Command: %s" % command)
        
        command = self.ascii2bin(command)
        return command

    def create_X10_command(self):
        #need to figure out how to get this the address
        options = {'On':'280',
                   'Off':'380',
                   'none':' '}
        house = '6' #"A" house code
        command  = '02 63 %s %s' % (house, DEVICES[self.device])
        command1 = '02 63 %s %s' % (house, options[self.action])
        log_str("Created X10 Command: %s" % command + command1)
        command = self.ascii2bin(command + command1)
        return command

    def day_of_week2num(self,day_of_week):
        days = {'Sun':0,
                'Mon':1,
                'Tue':2,
                'Wed':3,
                'Thu':4,
                'Fri':5,
                'Sat':6}
        return(days[day_of_week])

    def time_to_week_secs(self,days,hours,minutes,seconds):
        return(int(days*24*60*60+hours*60*60+minutes*60+seconds))

    def event_time_to_week_secs(self,days,time_str):
        time = self.time_to_week_secs(days,int(time_str[:-3]),int(time_str[-2:]),0)
        return time

    def ascii2bin(self, command):
        bytes = command.replace(' ','')
        binary = binascii.unhexlify(bytes)
        return(binary)
