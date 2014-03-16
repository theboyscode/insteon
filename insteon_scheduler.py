import asyncore
import socket
import binascii

import os

from operator import itemgetter


import csv
from event import *
#this is so I can post the values on git without having insteon address in it.
#expecting values HOST, PORT, DEVICES, FILENAME, PRESSURE, CITY_NAME
from values import *
from log_str import *


    
class Scheduler:
    def __init__(self,events):
        #denotes whether I have run the last event for that week
        #if I have run the last event I won't run any more
        #this is true if I have ran the last event and there is nothing more to run this week
        self.ran_last_event = False

        #number of events I have
        #I have to save the events because it is used to generate a new list every week
        self.events = events
                
        #here I make the event list, also runs the calcs to determine times for dawn/dusk
        #contains all the imported events to be run
        self.event_list = []
        self.make_event_list()

        #now I sort the events
        self.sort_event_list()

        #depending on what time the program is initially run I pick which event will go next
        self.next_event_index = self.determine_inital_event_index()

        #this is related to last event, it helps track when I start a new week
        self.last_time_ran = self.cur_week_secs()

    #takes the events and saves a list of tuples which can be easily sorted
    #the list contains [entry id (1 through x),time to run, command]
    #the entry really isn't used and I could get rid of it
    def make_event_list(self):
        log_str('number of event is: %i' %len(self.events))       
        for i in range(0,len(self.events)):
            self.event_list.append((i,self.events[i].get_command_time(),self.events[i].get_command()))
            
    #sorts the list of times and commands
    def sort_event_list(self):
        self.event_list = sorted(self.event_list, key=itemgetter(1))
        #print self.event_list

    #This is ran as specified in the main program, right now it is every 10 seconds
    def event_to_run(self):
        
        #check to see if I need to reset to a new week and start the sequence again.
        self.reset_to_new_week()

        #Here the next event is checked if it needs to be run.
        #I first check to see if I have run the last event
        if (self.ran_last_event ==  False):
            #break apart the parts list
            #this used to be outside the if -- MAKE SURE IT WORKS
            [next_num,next_time,next_command] = self.event_list[self.next_event_index]
            log_str("next: %i" %next_time)
            log_str("time: %i" %self.cur_week_secs())   

            #if I haven't run the last event I check to see if there are more events to run
            if (next_time < self.cur_week_secs()):
                log_str("This is the comparison %r" %(next_time < self.cur_week_secs()))
                log_str("There is a command to run")
                #if there is any event to run I return true and then get_next_event_command is run
                return True
        
        return False

    #handles proviging the next event and checking if I have run the last
    def get_next_event_command(self):
        
        cur_index = self.next_event_index
        self.next_event_index = self.next_event_index + 1
        if (self.next_event_index == len(self.events)):
            log_str("Ran last event of the week reseting to 0")
            self.next_event_index = 0
            self.ran_last_event = True
        else:
            self.ran_last_event = False
        log_str("just got the next command the index is %i" %cur_index)

        #When I run this need
        #break apart the parts list
        [next_num,next_time,next_command] = self.event_list[cur_index]
        return(next_command)

    #handles if I am in a new week
    def reset_to_new_week(self):
        if (self.cur_week_secs() < self.last_time_ran):
            self.ran_last_event = False

            #since the times for dawn and dusk change I have to reset the command times
            self.make_event_list()
            self.sort_event_list()

        self.last_time_ran = self.cur_week_secs()

    #once the scheduler is started I need to check what the first event is to run
    def determine_inital_event_index(self):
        log_str("in determin_inital_event")
        i = 0
        log_str(len(self.events))
        #just need the times here so make a list, must be a better way to do it
        times = [x[1] for x in self.event_list]
        while (times[i] < self.cur_week_secs()):
            i = i + 1
            if (i >= len(self.events)):
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
        self.events = []

        #timestamp when file is loaded.
        self.data_file_timestamp = os.stat(FILENAME).st_mtime
        
        #used to read in the events,this is temp and will need to change
        self.load_events()

        #now I start scheduling the events
        self.sched = Scheduler(self.events)

        #this seems shady
        self.event_handler = EventHandler(self.sched)

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
        #now I make a handler to handle the incoming messages
        self.event_handler.parse_mesg(binascii.hexlify(received).upper())

    def writable(self):
        
        #check to see if the data file is updated and if so reload everything
        if (self.data_file_updated()):
            self.reload_data_file()    
        
        if self.sched.event_to_run():
            self.buffer = self.sched.get_next_event_command()
        return (len(self.buffer) > 0)

    def data_file_updated(self):
        return (self.data_file_timestamp < os.stat(FILENAME).st_mtime)

    def reload_data_file(self):
        #timestamp when file is loaded.
        self.data_file_timestamp = os.stat(FILENAME).st_mtime
        #used to read in the events,this is temp and will need to change
        self.load_events()
        #now I start scheduling the events
        self.sched = Scheduler(self.events)

    def handle_write(self):
        sent = self.send(self.buffer)
        #need to put in some stuff here to break up the x10 commands and send them as two
        log_str("Sent: %s" %self.buffer)
        self.buffer = self.buffer[sent:]
        self.have_data = 0

    def load_events(self):
        #device,action,time,day of week,protocol,level
        #example: Hall,On,18:00,Mon,X10
        #also filters all the lines that start with #
        #make sure events is empty
        self.events = []
        fp  = file(FILENAME)
        input_file = csv.DictReader(filter(lambda row: row[0]!='#',fp))
        for row in input_file:
            self.events.append(Event(row["device"],row["action"],row["time"],row["day of week"],row["protocol"],row["level"]))
        fp.close()

#knows how to handle a received command
class EventHandler():
    def __init__(self,scheduler):
        self.scheduler = scheduler
        log_str("Made a handler")
        self.scheduler.events.append(Event('X10other','Off','12:00','Mon','X10','00'))
        self.scheduler.make_event_list()
        self.scheduler.sort_event_list()
        log_str("number of events %i" % len(self.scheduler.events))

    def parse_mesg(self,mesg):
        log_str("parsing %s" % mesg)
        #02502771F8000001CF1101

if __name__ == "__main__":

    c = SmartLincClient(HOST, PORT)
    print('Version 05MAR2014 v01d00')
    asyncore.loop(30) #this is where I set how often it loops the param is in seconds
    print('Past the sleep')
  
