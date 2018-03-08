import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.gen
from tornado.options import define, options
import os
import time
import re
import ConfigParser
import StringIO
import multiprocessing
import serialworker
import json
import sys
from subprocess import Popen, PIPE

import socket

define('port', default=8085, help='run on the given port', type=int)
 
clients = [] 

input_queue = multiprocessing.Queue()
output_queue = multiprocessing.Queue()

monitor_input_queue = multiprocessing.Queue()
monitor_output_queue = multiprocessing.Queue()

chat_input_queue = multiprocessing.Queue()
chat_output_queue = multiprocessing.Queue()

datLastNodeClientSend = time.time() # current time
datLastCrowdClientSend = time.time() # current time
blTrapResponse = 0
blChatConnected = 0
strChatHistory = ''
blChatBRFlag = 0
blNodeBRFlag = 0
strChatColor = ''
blDebugFlag = 0

global strCallSign
global strJSON
dicColour = {'1b':'#000000', #black
             '1':'#FF00FF',  #fuchsia
             '2':'#4169E1',  #royal blue
             '3':'#708090',  #slate grey
             '4':'#FF0000',  #red
             '5':'#008B8B',  #dark cyan
             '6':'#8B008B',  #dark magenta
             '7':'#FF8C00',  #dark orange
             '8':'#8B0000',  #dark red
             '9':'#00008B',  #dark blue
             '10':'#006400'  #dark green
            }

if os.path.isfile('/home/pi/tarpn-home-colors.json'):
    dicColour = json.load(open('/home/pi/tarpn-home-colors.json','r'))

# read node.ini variables
ini_str = '[root]\n' + open('/home/pi/node.ini','r').read()
ini_fp = StringIO.StringIO(ini_str)
config = ConfigParser.RawConfigParser()
config.readfp(ini_fp)
strNodeCall = config.get('root', 'nodecall').upper()
strNodeName = config.get('root', 'nodename').upper()
strCallSign = config.get('root', 'local-op-callsign').upper()
strPortFlag = config.get('root', 'tncpi-port01')
if strPortFlag == 'ENABLE':
    strPort1 = config.get('root', 'neighbor01').upper()
else:
    strPort1 = ''
strPortFlag = config.get('root', 'tncpi-port02')
if strPortFlag == 'ENABLE':
    strPort2 = config.get('root', 'neighbor02').upper()
else:
    strPort2 = ''
strPortFlag = config.get('root', 'tncpi-port03')
if strPortFlag == 'ENABLE':
    strPort3 = config.get('root', 'neighbor03').upper()
else:
    strPort3 = ''
strPortFlag = config.get('root', 'tncpi-port04')
if strPortFlag == 'ENABLE':
    strPort4 = config.get('root', 'neighbor04').upper()
else:
    strPort4 = ''

# build a JSON string from ini variables
strJSON = json.dumps({'NodeCall': strNodeCall, 'NodeName': strNodeName, 'CallSign': strCallSign, 'Port1': strPort1, 'Port2': strPort2, 'Port3': strPort3, 'Port4': strPort4})

def left(s, amount = 1):
    if (len(s) > amount):
        return s[:amount]
    else:
        return s

def right(s, amount = 1):
    if (len(s) > amount):
        return s[-amount:]
    else:
        return s
    
class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')
        
class StaticFileHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('main.js')
 
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print ('New connection')

        clients.append(self)
        time.sleep(1)
        ## passing in data rather than text
        self.write_message('^' + strJSON)

        strJSONVars = json.dumps({'ChatConnected': blChatConnected})
        self.write_message('~' + strJSONVars)

        strJSONVars = json.dumps({'ChatHistory': strChatHistory})
        self.write_message('`' + strJSONVars)

        self.write_message('Connected to node ' + strNodeName + '<br>')
 
    def on_close(self):
        print ('Connection closed')
        clients.remove(self)

    def shutdownserver(self):
        print ('Closing TARPN Home server')
        for c in clients:
            c.write_message('Server shutting down. Bye. Refresh the page to re-connect.')
        
        ## shutdown node worker
        input_queue.put('\03')
        time.sleep(1)
        input_queue.put('D')
        time.sleep(1)
        sp.close()
        
        ## shutdown monitor worker
        time.sleep(1)
        #monitor_input_queue.put('\03')
        #time.sleep(1)
        #monitor_input_queue.put('D')
        #time.sleep(1)
        sp_mon.close()
        time.sleep(1)
        
        ## shutdown chat worker
        time.sleep(1)
        chat_input_queue.put('\03')
        time.sleep(1)
        chat_input_queue.put('D')
        time.sleep(1)
        sp_chat.close()
        time.sleep(1)
        
        ## close websockets and get out
        self.close()
        clients.remove(self)
        print ('TARPN Home server closed')
        quit()

    def on_message(self, message):
        global datLastNodeClientSend
        global datLastCrowdClientSend
        global blDebugFlag
        
        if (blDebugFlag):
            print('Received from web: %s' % json.dumps(message))
            
        if len(message) > 0:
            if ((message[0] == '\\') and (len(message) >= 2)):
                if (message[1] == 'X'):
                    self.shutdownserver()
                elif (message[1:] == 'debug'):
                    if (blDebugFlag == 0):
                        blDebugFlag = 1
                        self.write_message('Debug mode ON. Logging begins.<br>')
                    else:
                        blDebugFlag = 0
                        self.write_message('Debug mode OFF, Logging ends.<br>')
            elif (message == 'RECONNECT!'):
                time.sleep(1)
                input_queue.put('\03')
                time.sleep(1)
                input_queue.put('D')
                time.sleep(1)
                input_queue.put('C SWITCH') 
            elif (message == '@RECONNECT!'):
                time.sleep(1)
                chat_input_queue.put('/B')
                time.sleep(1)
                chat_input_queue.put('B')
                time.sleep(1)
                chat_input_queue.put('\03')
                time.sleep(1)
                chat_input_queue.put('D')
                time.sleep(1)
                chat_input_queue.put('C SWITCH') 
                time.sleep(1)
                chat_input_queue.put('C CROWD S') 
            elif (message[0] == ':'):
                # : denotes a shell command
                cmd_msg = message[1:]
                p = Popen(cmd_msg, shell=True, stdout=PIPE, stderr=PIPE)
                out, err = p.communicate()
                self.write_message(':' + out)
            elif (message[0] == '@'):
                # @ denotes a chat command
                datLastCrowdClientSend = time.time() # current time
                cmd_msg = message[1:]
                chat_input_queue.put(cmd_msg)
            else:
                datLastNodeClientSend = time.time() # current time
                input_queue.put(message)
      	    
## check the serial queues for pending messages, and relay that to all connected clients
def checkQueue():
    global datLastNodeClientSend
    global datLastCrowdClientSend
    global blTrapResponse
    global blChatConnected
    global strChatHistory
    global blNodeBRFlag
    global blChatBRFlag
    global strChatColor
    global dicColour
    global blDebugFlag
    
    if not output_queue.empty():
        message = output_queue.get()
        if ((message != '') and (message[0:len(message)-2] == ' ')):
            ## eat the keepalive message of a single space
            message = ''
        ##print ('From node serial:' + message)
        ##if ((message != '')
	##      and (message[0:15] == '*** DISCONNECTED')):
        ##Try to reconnect
        ##   input_queue.put('c switch')
        ##elif ((message != '')
	##      and (message[0:22] != '*** CONNECTED to SWITCH')
        ##      and (message[0:7] != 'c switch')
        ##      and (message[0:7] != 'cmd:cmd:')):
        else:
            if (blDebugFlag):
                print(repr('From node serial:' + message))
                
            message = message.replace('\r\n','<br>')

            if (blNodeBRFlag == 1):
                message = time.strftime('%I:%M %p',time.localtime()) + ': ' + message
                blNodeBRFlag = 0
            if (message[-4:] == '<br>'):
                # set and save flag so next line causes a time prompt
                blNodeBRFlag = 1
            
            if (blDebugFlag):
                message = message + '(debug)'
                print(repr('To node web: ' + message))
                
            for c in clients:
                c.write_message(message)

    #elif not monitor_output_queue.empty():
    #    message = monitor_output_queue.get()
    #    message = message.replace('\r\n','<br>')
    #    #print ('From mon serial:' + message)
    #    for c in clients:
    #       c.write_message('!' + message)            
    elif not chat_output_queue.empty():
        message = chat_output_queue.get()
        if (blDebugFlag):
            print(repr('From crowd serial: ' + message))
        if ((message == '') or (message[0:len(message)-2] == '')):
            ## eat empty message
            message = '' 
        elif (message[len(message)-13:len(message)-2] == 'Keepalive!!'):
#        elif (message[len(message)-len('^^TARPN Home works great!^^')-2:len(message)-2] == '^^TARPN Home works great!^^'):
            ## eat the keepalive message
            message = ''
        else:
            intFirstChar = 0
            if ((message[0] == '\x1B') and (strChatColor == '')):
                intFirstChar = 2  # skip the color codes
                if message[1].encode('hex') in dicColour:
                    strHexColor = dicColour[message[1].encode('hex')]
                else:
                    for key, value in dicColour.iteritems():
                        if key in set(['1','2','3','4','5','6','7','8','9','10']):
                            #add the new key using the old key's color
                            dicColour[message[1].encode('hex')] = value
                            strHexColor = value
                            # remove the numeric version
                            del dicColour[key]
                            json.dump(dicColour,open('/home/pi/tarpn-home-colors.json','wb'))
                            break
                strChatColor = '<span style=\"color:' + strHexColor + ';font-weight:bold\">'
                    
            # make hyperlinks work
            anyURL = re.search('(?P<url>https?://[^\s]+)', message)
            if (anyURL):
                strURL = re.search('(?P<url>https?://[^\s]+)', message).group('url')
                message = message.replace(strURL,'<a href="' + strURL + '" target="_blank">' + strURL + '</a>')

            message = message[intFirstChar:].replace('\r\n','<br>')

            # Track crowd connection and pass state to clients
            if ((message != '') and (message[0:16] == 'Returned to Node')):
                blChatConnected = 0
                strJSONVars = json.dumps({'ChatConnected': blChatConnected})
                for c in clients:
                    c.write_message('~' + strJSONVars)
            elif ((message != '') and (message[0:15] == '[BPQChatServer-')):
                blChatConnected = 1
                strJSONVars = json.dumps({'ChatConnected': blChatConnected})
                for c in clients:
                    c.write_message('~' + strJSONVars)

            if (blChatBRFlag == 1):
                message = strChatColor + time.strftime('%I:%M %p',time.localtime()) + ': ' + message
                blChatBRFlag = 0
            elif (strChatColor != ''):
                message = '</span>' + strChatColor + message
            
            if (message[-4:] == '<br>'):
                # set and save flag so next line causes a time prompt
                blChatBRFlag = 1
                if (strChatColor != ''):
                    message = message.replace('<br>','</span><br>')
                    strChatColor = ''

            if (blDebugFlag):
                message = message + '(debug)'
                print(repr('To crowd web: ' + message))
            for c in clients:
                c.write_message('@' + message)            

            # save chat text to pass to client when needed
            if (blChatConnected == 1):
                strChatHistory = strChatHistory + message
                if len(strChatHistory) > 2000:
                    strChatHistory = strChatHistory[-2000:]
                                
    if time.time() - datLastNodeClientSend > 1200:
        ## greater then 20 minutes, so send keepalive to node port
        datLastNodeClientSend = time.time() # current time
        input_queue.put(' ') # just a space!

    if time.time() - datLastCrowdClientSend > 1200:
        ## greater then 20 minutes, so send keepalive to crowd port
        datLastCrowdClientSend = time.time() # current time
        chat_input_queue.put('/S ' + strCallSign + ' Keepalive!!')
        
    if not os.path.exists('remove_me_to_stop_server.txt'):
	## file is not there, so stop the server
        print ('Closing TARPN Home server')
        for c in clients:
            c.write_message('Server shutting down. Bye. Refresh the page to re-connect.')
        
        ## shutdown node worker
        input_queue.put('\03')
        time.sleep(1)
        input_queue.put('D')
        time.sleep(1)
        sp.close()
        
        ## shutdown monitor worker
        time.sleep(1)
        #monitor_input_queue.put('JHOST0\r')
        #monitor_input_queue.put('\03')
        #time.sleep(1)
        #monitor_input_queue.put('D')
        #time.sleep(1)
        sp_mon.close()
        time.sleep(1)
        
        ## shutdown chat worker
        time.sleep(1)
        chat_input_queue.put('\03')
        time.sleep(1)
        chat_input_queue.put('D')
        time.sleep(1)
        sp_chat.close()
        time.sleep(1)
        
        ## close websockets and get out
        input_queue.close()
        output_queue.close()
        monitor_input_queue.close()
        monitor_output_queue.close()
        chat_input_queue.close()
        chat_output_queue.close()

        print ('TARPN Home server closed')
        quit()
      
if __name__ == '__main__':
    keepRunning = True
    ## start the serial worker in background (as a deamon)
    sp = serialworker.SerialProcess(input_queue, output_queue, 4) ## port 4 for node commands
    sp.daemon = True
    sp.start()
    
    ## wait a second before sending first input
    time.sleep(1)
    input_queue.put('conok')
    input_queue.put('echo on')
    input_queue.put('autolf on')
    input_queue.put('mon off') ## always off
    time.sleep(2)
    input_queue.put('c switch')
    
    ## start the monitor serial worker in background (as a deamon)
    sp_mon = serialworker.SerialProcess(monitor_input_queue, monitor_output_queue, 5) ## port 5 for monitor
    sp_mon.daemon = True
    sp_mon.start()
     
    ## wait a second before sending first input
    #time.sleep(1)
    #monitor_input_queue.put('\x11\x18\x1BJHOST1\r')
    #monitor_input_queue.put('conok')
    #monitor_input_queue.put('echo off')
    #monitor_input_queue.put('autolf on')
    #monitor_input_queue.put('mon on') ## always on
    #monitor_input_queue.put('c switch')

    ## start the chat serial worker in background (as a deamon)
    sp_chat = serialworker.SerialProcess(chat_input_queue, chat_output_queue, 6) ## port 6 for chat
    sp_chat.daemon = True
    sp_chat.start()
     
    ## wait a second before sending first input
    time.sleep(1)
    chat_input_queue.put('conok')
    chat_input_queue.put('echo off')
    chat_input_queue.put('autolf on')
    chat_input_queue.put('mon off') ## always off
    chat_input_queue.put('c switch')

    tornado.options.parse_command_line()
          
    app = tornado.web.Application(
    	handlers=[
       	  (r'/', IndexHandler),
          (r'/static/(.*)', tornado.web.StaticFileHandler, {'path':  './'}),
          (r'/(favicon.ico)', tornado.web.StaticFileHandler, {'path':'./'}),
          (r'/ws', WebSocketHandler)
        ] 
    )    
    httpServer = tornado.httpserver.HTTPServer(app)
    httpServer.listen(options.port)
    ## print ('Listening on http port:', options.port)

    print ('Tarpn Home server is running')
    mainLoop = tornado.ioloop.IOLoop.instance()
    ## adjust the scheduler_interval according to the frames sent by the serial port
    scheduler_interval = 100
    scheduler = tornado.ioloop.PeriodicCallback(checkQueue, scheduler_interval, io_loop = mainLoop)
    scheduler.start()
    mainLoop.start()
