from log_str import *
from values import *
import binascii

class Trigger():
    def __init__(self, trigger, trigger_action, target, action, time_lag, time_min, time_max, protocol, level):

        self.trigger = DEVICES[trigger]
        self.trigger_action = self.get_trigger_action(trigger_action)
        self.target = DEVICES[target]
        self.action  = self.get_trigger_action(action)
        self.time_lag = time_lag
        self.time_lag_minutes = int(time_lag[3:5])
        self.time_lag_hours = int(time_lag[0:2])
        self.time_min = time_min
        self.time_max = time_max
        self.level = self.percent_to_level(level)
        self.protocol = protocol
        log_str('trigger.self.action = %s' % self.action)

    def get_trigger_action(self,action):
        options = {'On':'11',
                   'Off':'13'}
        return options[action]
    
    def percent_to_level(self,percent):
        level = hex(int(percent)*255/100)
        level = level[2:]
        level = level.upper()
        return level
        
    def get_command(self):
        return self.create_command()

    def create_command(self):
        if self.protocol == 'X10':
            return self.create_X10_command()
        elif self.protocol  == 'Insteon':
            return self.create_insteon_command()
        else:
            log_str("Command protocol does not match")
                
    def create_insteon_command(self):
        options = {'On':'0F 11 FF',
                   'Off':'0F 13 FF',
                   'none':'0F',
                   'Ramp':'0F 11'}
        #need to figure out how to get this the address

        if (self.action == 'Ramp'):
            command  = '02 62 %s %s %s' % (self.target,  options[self.action], self.level)
        elif (self.action == 'On'):
            command  = '02 62 %s %s' % (self.target,  options[self.action])
        elif (self.action == 'Off'):
            command  = '02 62 %s %s' % (self.target,  options[self.action])
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
        command  = '02 63 %s %s' % (house, DEVICES[self.target])
        command1 = '02 63 %s %s' % (house, options[self.target])
        log_str("Created X10 Command: %s" % command + command1)
        command = self.ascii2bin(command + command1)
        return command
   
    def ascii2bin(self, command):
        bytes = command.replace(' ','')
        binary = binascii.unhexlify(bytes)
        return(binary)
