from time import localtime, strftime
def log_str(str_to_log):
    #open log file
    filename = strftime("/home/pi/Insteon/log/%d_%b_%Y.log", localtime())
    LOG_FILE = open(filename,'a')
    LOG_FILE.write(str(str_to_log)+"\n")
    #print str(str_to_log)
    LOG_FILE.close()
