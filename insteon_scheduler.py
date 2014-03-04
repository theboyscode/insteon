import asyncore
import socket
import binascii
import time
import global_values
from time import localtime, strftime
import datetime
from astral import Astral
import csv
from values import *


def log_str(str_to_log):
    #open log file
    filename = strftime("/home/pi/Insteon/log/%d_%b_%Y.log", localtime())
    LOG_FILE = open(filename,'a')
    LOG_FILE.write(str(str_to_log)+"\n")
    #print str(str_to_log)
    LOG_FILE.close()
    
class Scheduler:
    def __init__(self,events):
        #contains all the imported events to be run
        self.sched_events = events
        self.num_events = len(self.sched_events)

        #denotes whether we have run the last event for that week
        #if we have run the last event we won't run any more
        #this is true if we have ran the last event and there is nothing more to run this week
        self.ran_last_event = False

        #depending on what time the program is initially run we pick which event will go next
        self.next_event = self.determine_inital_event()

        #this is related to last event, it helps track when we start a new week
        self.last_time_ran = self.cur_week_secs()

       
    #This is ran as specified in the main program, right now it is every 10 seconds
    def event_to_run(self):
        ###log_str("in event to run. Ran last event is %r" %(self.ran_last_event))

        #check to see if we need to reset to a new week and start the sequence again.
        self.reset_to_new_week()

        #Here the next event is checked if it needs to be run.
        #We first check to see if we have run the last event
        if (self.ran_last_event ==  False):
            log_str("next: %i" %self.sched_events[self.next_event].event_week_secs)
            log_str("time: %i" %self.cur_week_secs())

            #if we haven't run the last event we check to see if there are more events to run
            if (self.sched_events[self.next_event].event_week_secs < self.cur_week_secs()):
                log_str("This is the comparison %r" %(self.sched_events[self.next_event].event_week_secs < self.cur_week_secs()))
                log_str("There is a command to run")
                #if there is any event to run we return true and then get_next_event_command is run
                return True
        return False

    #handles proviging the next event and checking if we have run the last
    def get_next_event_command(self):
        cur_index = self.next_event
        self.next_event = self.next_event + 1
        if (self.next_event == self.num_events):
            log_str("Ran last event of the week reseting to 0")
            self.next_event = 0
            self.ran_last_event = True
        else:
            self.ran_last_event = False
        log_str("just got the next command the index is %i" %cur_index)

        #When we run this need 
        return(self.sched_events[cur_index].command)

    #handles if we are in a new week
    def reset_to_new_week(self):
        if (self.cur_week_secs() < self.last_time_ran):
            self.ran_last_event = False

        self.last_time_ran = self.cur_week_secs()


    #once the scheduler is started we need to check what the first event is to run
    def determine_inital_event(self):
        log_str("in determin_inital_event")
        i = 0
        log_str(self.num_events)
        while (self.sched_events[i].event_week_secs < self.cur_week_secs()):
            i = i + 1
            if (i >= self.num_events):
                log_str('i is: %i' %i)
                log_str('No events to schedule')
                self.ran_last_event = True
                break
        log_str("Next event to run is event %i" %i)
        return i
        
    #gets the curr week seconds from the OS
    def cur_week_secs(self):
        curr_time = localtime()
        days = int(strftime("%w", curr_time ))
        hours = int(strftime("%H", curr_time ))
        minutes = int(strftime("%M", curr_time))
        seconds = int(strftime("%S", curr_time))
        #print "weeksec is: %i" %self.time_to_week_secs(days,hours, minutes, seconds)
        return (self.time_to_week_secs(days,hours, minutes, seconds))

    def time_to_week_secs(self,days,hours,minutes,seconds):
        return(int(days*24*60*60+hours*60*60+minutes*60+seconds))

    def event_time_to_week_secs(self,days,time_str):
        return self.time_to_week_secs(days,int(time_str[:-3]),int(time_str[-2:]),0)
        
class SmartLincClient(asyncore.dispatcher):

    def __init__(self, host, port):
        #Create a list of events
        events = []
        
        #used to read in the events,this is temp and will need to change
        self.load_events(events)

        #now we start scheduling the events
        self.sched = Scheduler(events)

        #upon initial running
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.buffer = ''

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        received = self.recv(1024)
        log_str("Received: %s" % binascii.hexlify(received).upper())

    def writable(self):
        if self.sched.event_to_run():
            self.buffer = self.sched.get_next_event_command()
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        log_str("Sent: %s" %self.buffer)
        self.buffer = self.buffer[sent:]
        self.have_data = 0

    def load_events(self,events):
        #device,action,time,day of week,protocol,level
        #example: Hall,On,18:00,Mon,X10
        input_file = csv.DictReader(open(FILENAME))
        for row in input_file:
            events.append(Event(row["device"],row["action"],row["time"],row["day of week"],row["protocol"],row["level"]))

class Event():
    def __init__(self, device, action,time, day_of_week, protocol,percent):
        self.device = device
        self.action  = action
        self.time = time
        self.day_of_week = day_of_week
        self.level = self.percent_to_level(percent)
        log_str('day of week = %s' % (self.day_of_week))
        self.protocol = protocol
        self.day_of_week_num = self.day_of_week2num(self.day_of_week)
        self.event_week_secs = self.event_time_to_week_secs(self.day_of_week_num,self.time)
        self.command = self.create_command()
        log_str("weekseconds event time is: %i" %self.event_week_secs)

    def get_command(self):
        a=0
        #this is where we will include the time of dawn / dusk
        #steps move all the things to generate a command from __init__ down to here
            #this includes day of week num and event week secs and command
        #instead of returning the command up higher need to call get command.
        #when get__command is called need to check if it is dusk/dawn and then handle the time.
            #that can probaly be put in time_to_week_secs

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
        command  = '02 63 %s %s %s' % (house, DEVICES[self.device],  options[self.action])
        log_str("Created Command: %s" % command)
        command = self.ascii2bin(command)
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
        time = 0
        if (time_str == 'dawn'):
            time = 1#do something
            
        elif (time_str == 'dusk'):
            #do something else
            time = 2
        else:
            time = self.time_to_week_secs(days,int(time_str[:-3]),int(time_str[-2:]),0)
        return time

    def ascii2bin(self, command):
        bytes = command.replace(' ','')
        log_str("Creating command in ascii2bin: %s" % bytes)
        binary = binascii.unhexlify(bytes)
        return(binary)

if __name__ == "__main__":

    c = SmartLincClient(HOST, PORT)
    print('Version 02MAR2014 v00d01')
    asyncore.loop(30) #this is where we set how often it loops the param is in seconds

    #asyncore.loop(timeout=10, count=1)
    print('Past the sleep')
  
