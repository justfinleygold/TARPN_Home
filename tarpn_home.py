import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.gen
from tornado.options import define, options
import os, uuid
from datetime import date
import time
import re
import ConfigParser
import StringIO
import multiprocessing
import serialworker
import json
import sys
import getpass  # to get logged in user
from subprocess import Popen, PIPE
import socket

NODE_PREFIX = '\x10'
CHAT_PREFIX = '\x11'
HIDDEN_PREFIX = '\x12'
DATA_PREFIX = '\x13'

define('port', default=8085, help='run on the given port', type=int)
 
clients = [] 

node_input_queue = multiprocessing.Queue()
node_output_queue = multiprocessing.Queue()

chat_input_queue = multiprocessing.Queue()
chat_output_queue = multiprocessing.Queue()

hidden_input_queue = multiprocessing.Queue()
hidden_output_queue = multiprocessing.Queue()

datLastNodeClientSend = time.time() # current time
datLastChatClientSend = time.time()
datLastChatTyped = time.time()
datLastChatKeepAlive = time.time()
datLastMailCheck = time.time()

blTrapResponse = 0
blChatJoined = 0 
blChatInSwitch = 0
blNodeInSwitch = 0
blCheckChatPort = 0
blChatIsAlive = 0 
blNodeIsAlive = 0 
blChatAvailable = 0
blBBSCheck = 0
blInBBS = 0
intChatAlertVisual = 3 # 0 = none, 1 = unfocused, 2 = 5 minutes,, 3 = inactive or unfocused
strChatSoundFile = 'Default'
intShowHints = 1
intShowCommands = 1
intChatAlertSound = 2 # 0 = none, 1 = unfocused, 2 = 5 minutes,, 3 = inactive or unfocused, 4 = every message
intIgnoreChatJoins = 1
intUseBBS = 1
intIgnoreBBSKilled = 1;
strBBSSoundFile = 'Default'
blChatBRFlag = 0 
blNodeBRFlag = 0 
strChatColor = ''
strChatName = ''
strNodeColor = ''
blDebugFlag = 0
blMonitorFlag = 0
datCurDate = date.today()
strIniFile = '/home/pi/TARPN_Home.ini'
datChatBufferWaitStart = time.time()
strChatBufferWaitFor = ""
strChatBuffer = ""
datHiddenBufferWaitStart = time.time()
strHiddenBufferWaitFor = ""
strHiddenBuffer = ""
intHiddenPromptCount = 0
intHiddenPromptsNeeded = 0
lstChatter = []
blIgnoreChatSerial = 0
blIgnoreNodeSerial = 0
lstBBSMsg = []
strBBSPrompt = ''
blQueuesAlive = False
strMyChatStatus = 'IDL'
datLastChatIdleCheck = time.time()
strMapPos = ''

#chat colors
dicColour = {'1a':'#0000ff', #blue
			 '5b':'#ff0000', #red
			 '3c':'#006400', #dark green
			 '4c':'#ff00ff', #fuchsia
			 '1b':'#00cccc', #cyan
			 '5f':'#708090', #grey
			 '60':'#b50000', #maroon
			 '63':'#00aa00', #light green
			 '13':'#ff7300', #light orange
			 '37':'#4169e1', #light blue
			 '34':'#d99f0d', #gold
			 '1':'#92623a',  #brown
			 '2':'#808000',  #olive
			 '3':'#880088',  #purple
			 '4':'#008b8b',  #teal
			 '5':'#ff66ff',  #pink
			 '6':'#4169e1',  #orange
			 '7':'#FF8C00',  #dark orange
			 '8':'#a360ff',  #light purple
			 '9':'#ffbb00',  #dark yellow
			 '10':'#0080e2', #bright blue
			# reserve colors
			 '11':'#006688', #bluish
			 '12':'#66b3ff', #sky blue
			 '14':'#33ff33', #lime green
			 '15':'#ff4d4d', #light red
			 '16':'#669999', #light grey
			 '17':'#b3b3b3', #bright grey
			 '18':'#ff9999', #peach
			 '19':'#663d00', #dark brown
			 '20':'#cccc00', #pale yellow
			 '21':'#00802b'  #some green
			}

if getpass.getuser() == 'pi':
	strDir = '/home/pi'
else:
	strDir = '/var/log'
strChatLogFile = strDir + '/TARPN_Home_Chat.log'
strChatLogRawFile = strDir + '/TARPN_Home_Chat_Raw.log'
strNodeLogFile = strDir + '/TARPN_Home_Node.log'

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
strPortFlag = config.get('root', 'tncpi-port05')
if strPortFlag == 'ENABLE':
	strPort5 = config.get('root', 'neighbor05').upper()
else:
	strPort5 = ''
strPortFlag = config.get('root', 'tncpi-port06')
if strPortFlag == 'ENABLE':
	strPort6 = config.get('root', 'neighbor06').upper()
else:
	strPort6 = ''
ini_fp.close()

# build a JSON string from node.ini variables for the Node
strNodeJSON = json.dumps({'NodeCall': strNodeCall, 'NodeName': strNodeName, 'CallSign': strCallSign, 'Port1': strPort1, 'Port2': strPort2, 'Port3': strPort3, 'Port4': strPort4, 'Port5': strPort5, 'Port6': strPort6})

# Read TARPN Home Ini File
config = ConfigParser.ConfigParser()
if not os.path.exists(strIniFile):
	# build and save new ini entries
	config.add_section("Main")
	config.set("Main", "ShowHints", "1")
	config.set("Main", "ShowCommands", "1")
	config.add_section("BBS")
	config.set("BBS", "UseBBS", "1")
	config.set("BBS","IgnoreBBSKilled","1")
	config.set("BBS","SoundFile","Default")
	config.add_section("Chat")
	config.set("Chat", "AlertSound", "2")
	config.set("Chat", "SoundFile", "Default")
	config.set("Chat", "AlertVisual", "3")
	config.set("Chat", "IgnoreJoins", "1")

	try:
		with open(strIniFile, "wb") as config_file:
			config.write(config_file)   
	except:
		print ('Problems saving to /home/pi/TARPN_Home.ini')     
else:
	config.read(strIniFile)

# read values from the TARPN Home ini file
intShowHints = int(config.get("Main", "ShowHints"))
intShowCommands = int(config.get("Main", "ShowCommands"))
intChatAlertSound = int(config.get("Chat", "AlertSound"))
strChatSoundFile = config.get("Chat", "SoundFile")
intChatAlertVisual = int(config.get("Chat", "AlertVisual"))
intIgnoreChatJoins = int(config.get("Chat", "IgnoreJoins"))
intUseBBS = int(config.get("BBS", "UseBBS"))
intIgnoreBBSKilled = int(config.get("BBS", "IgnoreBBSKilled"))
strBBSSoundFile = config.get("BBS", "SoundFile")
	
# read expert BBS prompt from linmail.cfg
try:
	ini_str = open('/home/pi/bpq/linmail.cfg','r').read()
	intStart = ini_str.find('ExpertPrompt')
	if (intStart > -1):
		intStart = intStart + 16
		intEnd = ini_str.find(';',intStart) 
		intEnd = intEnd - 1	
		strBBSPrompt = ini_str[intStart:intEnd]
		strBBSPrompt = strBBSPrompt.replace('$x','').replace('\\r\\n','') + '<br>'
except:
	strBBSPrompt = ''
ini_str = ''

# read Map Coords from chatconfig.cfg
try:
	ini_str = open('/home/pi/bpq/chatconfig.cfg','r').read()
	intStart = ini_str.find('MapPosition')
	if (intStart > -1):
		intStart = intStart + 15
		intEnd = ini_str.find(';',intStart) 
		intEnd = intEnd - 1	
		strMapPos = ini_str[intStart:intEnd]
		strMapPos = strMapPos.replace('\\r\\n','')
except:
	strMapPos = ''
ini_str = ''

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

def SaveIniFile():
	global intShowHints
	global intShowCommands
	global intChatAlertSound
	global intChatAlertVisual
	global intIgnoreChatJoins
	global intUseBBS
	global intIgnoreBBSKilled
	global strIniFile
	
	config = ConfigParser.ConfigParser()
	# build and save ini entries
	config.add_section("Main")
	config.set("Main", "ShowHints", intShowHints)
	config.set("Main", "ShowCommands", intShowCommands)
	config.add_section("BBS")
	config.set("BBS", "UseBBS", intUseBBS)
	config.set("BBS", "IgnoreBBSKilled", intIgnoreBBSKilled)
	config.set("BBS", "SoundFile", strBBSSoundFile)
	config.add_section("Chat")
	config.set("Chat", "AlertSound", intChatAlertSound)
	config.set("Chat", "AlertVisual", intChatAlertVisual)
	config.set("Chat", "IgnoreJoins", intIgnoreChatJoins)
	config.set("Chat", "SoundFile", strChatSoundFile)

	try:
		with open(strIniFile, "wb") as config_file:
			config.write(config_file)
	except:
		print ('Problems saving to /home/pi/TARPN_Home.ini')
		
def readChatLog():
	# read chat log
	strLocalText = ""
	if os.path.exists(strChatLogFile):
		f = open(strChatLogFile, "r")
		strLocalText = f.read()
		strLocalText = right(strLocalText, 10000) # only the last 10000 characters
		strLocalText = strLocalText.replace('\r\n','<br>')
		strLocalText = json.dumps({'ChatHistory': strLocalText})
		f.close()
	return strLocalText

def clearAllLogs():
	try:
		f = open(strChatLogFile,'w')
		f.close()	
		f = open(strChatLogRawFile,'w')
		f.close()	
		f = open(strNodeLogFile,'w')
		f.close()
	except:
		print ('Failed to clear logs')	
		
def shutdownServer(self):
	global blQueuesAlive
	
	print ('Closing TARPN Home server')
	for c in clients:
		c.write_message('HOME: Rebooting app server. Bye. Refresh the page to re-connect.')
		c.write_message(CHAT_PREFIX + 'HOME: Rebooting app server. Bye. Refresh the page to re-connect.')
		
	# shutdown node queue
	if (blQueuesAlive == 1):
		try:
			node_input_queue.put('\03')
			node_input_queue.put('D')
			time.sleep(1)
			sp.close()
		except AssertionError:
			blQueuesAlive = 0
			print ('Node queue is off and disabled')
	
	# shutdown hidden queue
	if (blQueuesAlive == 1):
		try:
			hidden_input_queue.put('\03')
			hidden_input_queue.put('D')
			time.sleep(1)
			sp_hidden.close()
		except AssertionError:
			blQueuesAlive = 0
			print ('Hidden queue is off and disabled')
			
	# shutdown chat queue
	if (blQueuesAlive == 1):
		try:
			chat_input_queue.put('\03')
			chat_input_queue.put('D')
			time.sleep(1)
			sp_chat.close()
		except AssertionError:
			blQueuesAlive = 0
			print ('Chat queue is off and disabled')
		 
	# close websockets and get out
	if (blQueuesAlive == 1):
		node_input_queue.close()
		node_output_queue.close()
		hidden_input_queue.close()
		hidden_output_queue.close()
		chat_input_queue.close()
		chat_output_queue.close()

	## close websockets and get out
	#self.close()
	print ('TARPN Home server closed')
	quit()

class UploadHandler(tornado.web.RequestHandler):	
	def post(self):
		fileinfo = self.request.files['file_arg'][0]
		fname = fileinfo['filename']
		fh = open('uploads/' + fname, 'w')
		fh.write(fileinfo['body'])
		self.finish() 
        
class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('index.html')
	
class AboutHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('about.html')

class HelpHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('help.html')

class StaticFileHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('main.js')
	   
class WebSocketHandler(tornado.websocket.WebSocketHandler):
	def open(self):
		global lstChatter
		global intChatAlertSound
		global strChatSoundFile
		global intChatAlertVisual
		global intIgnoreChatJoins
		global intShowHints
		global intShowCommands
		global intUseBBS
		global intIgnoreBBSKilled
		global strBBSSoundFile
		
		print ('New connection')

		clients.append(self)
		time.sleep(1)
		# pass ini settings to screen
		self.write_message(DATA_PREFIX + 'ini' + strNodeJSON)

		#options
		strJSONVars = json.dumps({'ChatAlertSound': intChatAlertSound, 'ChatSoundFile': strChatSoundFile, 'ChatAlertVisual': intChatAlertVisual,'IgnoreChatJoins': intIgnoreChatJoins,'ShowHints': intShowHints,'ShowCommands': intShowCommands,'UseBBS': intUseBBS,'IgnoreBBSKilled': intIgnoreBBSKilled,'BBSSoundFile':strBBSSoundFile})
		self.write_message(DATA_PREFIX + 'options' + strJSONVars)

		#state vars
		strJSONVars = json.dumps({'ChatJoined': blChatJoined,'ChatInSwitch': blChatInSwitch,'NodeInSwitch': blNodeInSwitch})
		self.write_message(DATA_PREFIX + 'state' + strJSONVars)

		# read chat log
		strChatLog = readChatLog()
		if strChatLog != '':
			self.write_message(DATA_PREFIX + 'chat_history' + strChatLog)
			strChatLog = ''
		if (len(lstChatter) > 0):
			sendChatListToScreens()
		self.write_message('Connected to node ' + strNodeName + '<br>')
 
	def on_close(self):
		print ('Connection closed')
		clients.remove(self)
  
	# Messages received from a web screen
	def on_message(self, message):
		global datLastNodeClientSend
		global datLastChatClientSend
		global datLastChatKeepAlive
		global datLastChatTyped
		global blDebugFlag
		global blMonitorFlag
		global blChatAvailable
		global intChatAlertSound
		global strChatSoundFile
		global intChatAlertVisual
		global intIgnoreChatJoins
		global intShowHints
		global intShowCommands
		global intUseBBS
		global intIgnoreBBSKilled
		global strBBSSoundFile
		global blIgnoreNodeSerial
		global blIgnoreChatSerial
		global strHiddenBufferWaitFor
		global datHiddenBufferWaitStart
		global strHiddenBuffer
		global intHiddenPromptCount
		global intHiddenPromptsNeeded
		global blInBBS
		global blQueuesAlive
		global strChatName
		global strMyChatStatus

		#print('Received from web: ' + repr(message))
		if (blDebugFlag):
			print('Received from web: %s' % json.dumps(message))
			
		if len(message) > 0:
			if ((message[0] == DATA_PREFIX) and (len(message) > 1)):
				if (message[1:] == 'shutdown'):
					shutdownServer(self)
				elif (message[1:] == 'clear_logs'):
					clearAllLogs()						
				elif (message[1:7] == 'mon_on'):
					node_input_queue.put('B')
					node_input_queue.put('MON ON')
					node_input_queue.put('C SWITCH')
					time.sleep(1)
					blMonitorFlag = 1
				elif (message[1:8] == 'mon_off'):
					blMonitorFlag = 0
					node_input_queue.put('B')
					node_input_queue.put('MON OFF')
					node_input_queue.put('C SWITCH')                     
					time.sleep(1)
				elif (message[1:8] == 'options'):
					#read options from screen
					my_obj = json.loads(message[8:])
					intChatAlertSound = int(my_obj['ChatAlertSound'])
					strChatSoundFile = my_obj['ChatSoundFile']
					intChatAlertVisual = int(my_obj['ChatAlertVisual'])
					intIgnoreChatJoins = int(my_obj['IgnoreChatJoins'])
					intShowHints = int(my_obj['ShowHints'])
					intShowCommands = int(my_obj['ShowCommands'])
					intUseBBS = int(my_obj['UseBBS'])
					intIgnoreBBSKilled = int(my_obj['IgnoreBBSKilled'])
					strBBSSoundFile = my_obj['BBSSoundFile']
					SaveIniFile()
			elif ((message[0] == CHAT_PREFIX) and (len(message) > 1)):
				if (message[1:8] == 'connect'): # connect chat pane
					chat_input_queue.put('C SWITCH S') 
					time.sleep(1)
				elif (message[1:11] == 'disconnect'): # disconnect chat pane
					chat_input_queue.put('/B')
					chat_input_queue.put('B')
					chat_input_queue.put('\03')
					chat_input_queue.put('D')
					time.sleep(1)
				else:
					# normal chat text
					datLastChatClientSend = time.time() # current time
					datLastChatTyped = datLastChatClientSend
					datLastChatKeepAlive = datLastChatClientSend
					cmd_msg = message[1:]
					chat_input_queue.put(cmd_msg)
					if (strMyChatStatus != 'ACT'):
						strMyChatStatus = 'ACT'						
			elif ((message[0] == NODE_PREFIX) and (len(message) > 1)):
				if (message[1:8] == 'connect'): # connect node pane
					node_input_queue.put('C SWITCH S') 
					time.sleep(1)
				elif (message[1:11] == 'disconnect'): # disconnect node pane
					node_input_queue.put('\03')
					time.sleep(1)
					node_input_queue.put('D')
					time.sleep(1)
			elif ((message[0] == HIDDEN_PREFIX) and (blQueuesAlive == 1)):
				# A hidden command
				cmd_msg = message[1:]
				if (cmd_msg == 'bbs_enter'):
					#print ('In BBS')
					blInBBS = 1
					intHiddenPromptCount = 0
					intHiddenPromptsNeeded = 2
					# set it to buffer the entire text
					strHiddenBufferWaitFor = "bbs_list"
					datHiddenBufferWaitStart = time.time()
					hidden_input_queue.put('BBS')
					#time.sleep(1)
					hidden_input_queue.put('LL 100')					
					time.sleep(1)
				elif (cmd_msg == 'bbs_exit'):
					#print ('Exit BBS')
					hidden_input_queue.put('NODE')
					#time.sleep(1)
					blInBBS = 0
				elif (cmd_msg == 'bbs_refresh'):
					intHiddenPromptCount = 0
					intHiddenPromptsNeeded = 1
					strHiddenBufferWaitFor = "bbs_list"
					datHiddenBufferWaitStart = time.time()
					hidden_input_queue.put('LL 100')					
				elif (cmd_msg[0:12] == 'bbs_read_msg'):
					strMsgNum = cmd_msg[12:]
					intHiddenPromptCount = 0
					intHiddenPromptsNeeded = 1
					hidden_input_queue.put('R ' + cmd_msg[12:])	
					# set it to buffer the entire text
					strHiddenBufferWaitFor = "bbs_read_msg"
					datHiddenBufferWaitStart = time.time()				
					#time.sleep(1)
				elif (cmd_msg[0:12] == 'bbs_kill_msg'):
					strMsgNum = cmd_msg[12:]
					intHiddenPromptCount = 0
					intHiddenPromptsNeeded = 1
					hidden_input_queue.put('K ' + cmd_msg[12:])	
					# set it to buffer the entire text
					strHiddenBufferWaitFor = "bbs_kill_msg"
					datHiddenBufferWaitStart = time.time()				
					#time.sleep(1)
				elif (cmd_msg[0:11] == 'bbs_new_msg'):
					my_obj = json.loads(cmd_msg[11:])
					strInit = my_obj['InitStr']
					strSubject = my_obj['Subject']
					strMsg = my_obj['Message']
					hidden_input_queue.put(my_obj['InitStr'])
					if (my_obj['Subject'] != ''):
						hidden_input_queue.put(my_obj['Subject'])
					hidden_input_queue.put(my_obj['Message'])
					time.sleep(2)		
					intHiddenPromptCount = 0
					intHiddenPromptsNeeded = 4
					strHiddenBufferWaitFor = "bbs_list"
					datHiddenBufferWaitStart = time.time()										
					hidden_input_queue.put('LL 100')					
			else:
				if (message[0:2] == '$:'):
					# : denotes a shell command
					cmd_msg = message[2:]
					p = Popen(cmd_msg, shell=True, stdout=PIPE, stderr=PIPE)
					out, err = p.communicate()
					# send to current node window only
					self.write_message(out)
				elif (message[0:6] == 'debug!'):
					if (blDebugFlag == 0):
						blDebugFlag = 1
						self.write_message('Debug mode ON. Logging begins.<br>')
					else:
						blDebugFlag = 0
						self.write_message('Debug mode OFF, Logging ends.<br>')
				elif (message[0:9] == 'tarpnkafg'): 
					for c in clients:
						c.write_message(DATA_PREFIX + '.^.' + 'hi')
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						if (strChatName != ''):
							strTemp = strChatName
						else:
							strTemp = strCallSign
						c.write_message(DATA_PREFIX + '.^.' + strTemp + ' is a rockin packeteer on...\r\n')
						time.sleep(2)
						c.write_message(DATA_PREFIX + '.^.' + '\\  --------------------------   \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '   \\  ---------------           \\   \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '    |  \\  ------       \\          \\   \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '    |    \\       \\        \\        \\  \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '    |     \\       \\        \\        |  \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '    |      |       |        |       |   \r\n')
						time.sleep(0.5)
						c.write_message(DATA_PREFIX + '.^.' + '    \\/     \\/      \\/       \\/      \\/  \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + 'd888888b  .d8b.  d8888b. d8888b. d8b   db\r\n')
						c.write_message(DATA_PREFIX + '.^.' + '`~~88~~` d8` `8b 88  `8D 88  `8D 888o  88\r\n')
						c.write_message(DATA_PREFIX + '.^.' + '   88    88ooo88 88oobY` 88oodD` 88V8o 88\r\n')
						c.write_message(DATA_PREFIX + '.^.' + '   88    88~~~88 88`8b   88~~~   88 V8o88\r\n')
						c.write_message(DATA_PREFIX + '.^.' + '   88    88   88 88 `88. 88      88  V888\r\n')
						c.write_message(DATA_PREFIX + '.^.' + '   YP    YP   YP 88   YD 88      VP   V8P\r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + ' \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + 'Wherever you go, well then there you are. But Home is where the heart is. \xF0\x9F\x98\x85 \r\n')
						time.sleep(1)
						c.write_message(DATA_PREFIX + '.^.' + '73 de Fin NC4FG and goodbye! \r\n')
						time.sleep(3)
						c.write_message(DATA_PREFIX + '.^.' + 'bye')
				else:
					# defaults to a node command
					datLastNodeClientSend = time.time() # current time
					node_input_queue.put(message)

def sendStateFlags(strExtra):
	global blChatJoined
	global blChatInSwitch
	global blNodeInSwitch
	global blDebugFlag
 
	if (blDebugFlag):
		print ('Chat state update: at ' + time.strftime('%I:%M %p',time.localtime()))
	strJSONVars = json.dumps({'ChatJoined': blChatJoined,'ChatInSwitch': blChatInSwitch,'NodeInSwitch': blNodeInSwitch})
	for c in clients:
		c.write_message(DATA_PREFIX + 'state' + strJSONVars)
		if (strExtra != ''):
			c.write_message(strExtra)

def sendChatStatusUpdate(intIndex, strStatus, strTime):
	global lstChatter   
	for c in clients:
		c.write_message(DATA_PREFIX + 'chat_status' + str(intIndex) + ':' + strStatus + strTime)                

def sendChatListToScreens():
	global lstChatter   
	strJSON = json.dumps(lstChatter).replace('\\','').replace('["','[').replace('"]',']').replace('"{','{').replace('}"','}')
	for c in clients:
		c.write_message(DATA_PREFIX + 'chat_list' + strJSON)                

def RebuildChatList(strIn):
	global lstChatter
	global strChatName
	global strCallSign
	global datLastChatIdleCheck
	
	#print ('RebuildChatList Buffer: ' + repr(strIn))
	del lstChatter[:]
	intStartParse = strIn.find('Station(s) connected:<br>') + 25
	intEndParse = intStartParse + strIn[intStartParse:].find('<br>')
	strCurColor = '#000000'
 
	while (intStartParse >= 0) and (intStartParse < len(strIn)):
		intEndParse = strIn[intStartParse:].find('<br>')
		if intEndParse < 0:
			break
		else:
			intEndParse = intStartParse + intEndParse + 4
			strLine = strIn[intStartParse:intEndParse]
			intTemp = strLine.find('color:')
			if (intTemp > 0):
				strCurColor = strLine[intTemp + 6: intTemp+13]
				intTemp = strLine.find('>')
				if (intTemp > 0):
					strLine = strLine[intTemp+1:]                       
			intComma = strLine.find(',')
			strCall = strLine[0:strLine.find(' ')]
			if (strCall == strCallSign):
				strStatus = strMyChatStatus
			else:
				strStatus = 'IDL'
			strTime = time.strftime('%m-%d-%Y %H:%M',time.localtime(time.time()))
			strName = strLine[strLine[0:intComma].rfind(' ')+1:intComma]			
			strJSON = json.dumps({'Name':strName, 'Call':strCall,'Color':strCurColor,'Status':strStatus,'Time':strTime})
			lstChatter.append(strJSON)
			if (strCall == strCallSign):
				strChatName = strName
		intStartParse = intEndParse
	# update screens with JSON
	sendChatListToScreens()
	datLastChatIdleCheck = time.time()

def UpdateChatList(strIn):
	global lstChatter
	global strChatName
	global strCallSign
	global datLastChatIdleCheck
	
	#print ('UpdateChatList Buffer: ' + repr(strIn))
	intStartParse = strIn.find('Station(s) connected:<br>') + 25
	intEndParse = intStartParse + strIn[intStartParse:].find('<br>')
	strCurColor = '#000000'
 
	while (intStartParse >= 0) and (intStartParse < len(strIn)):
		intEndParse = strIn[intStartParse:].find('<br>')
		if intEndParse < 0:
			break
		else:
			intEndParse = intStartParse + intEndParse + 4
			strLine = strIn[intStartParse:intEndParse]
			intTemp = strLine.find('color:')
			if (intTemp > 0):
				strCurColor = strLine[intTemp + 6: intTemp+13]
				intTemp = strLine.find('>')
				if (intTemp > 0):
					strLine = strLine[intTemp+1:]                       
			intComma = strLine.find(',')
			strCall = strLine[0:strLine.find(' ')]
			strName = strLine[strLine[0:intComma].rfind(' ')+1:intComma]			
			blFound = False
			# find Call in existing list
			for i, obj in enumerate(lstChatter):
				d = json.loads(obj)
				if (d['Call'] == strCall):
					blFound = True
					strStatus = d['Status']
					strTime = d['Time']
					break
			if (blFound == False):
				strStatus = 'IDL'
				strTime = time.strftime('%m-%d-%Y %H:%M',time.localtime(time.time()))
			if (strCall == strCallSign):
				strStatus = strMyChatStatus
			strJSON = json.dumps({'Name':strName, 'Call':strCall,'Color':strCurColor,'Status':strStatus,'Time':strTime})
			if (blFound == False):
				lstChatter.append(strJSON)
			else:
				lstChatter[i] = strJSON
			if (strCall == strCallSign):
				strChatName = strName
		intStartParse = intEndParse
	# update screens with JSON
	sendChatListToScreens()
	datLastChatIdleCheck = time.time()
		
def processHiddenBuffer():
	global strHiddenBufferWaitFor
	global strHiddenBuffer
	global intHiddenPromptCount
	global intHiddenPromptsNeeded
	
	if (strHiddenBufferWaitFor == 'bbs_list'):
		RebuildBBSList(strHiddenBuffer)
	elif (strHiddenBufferWaitFor == 'bbs_read_msg'):
		read_bbs_message(strHiddenBuffer)
	elif (strHiddenBufferWaitFor == 'bbs_kill_msg'):
		read_bbs_message(strHiddenBuffer)
	strHiddenBufferWaitFor = ''
	strHiddenBuffer = ''
	intHiddenPromptCount = 0
	intHiddenPromptsNeeded = 0

def RebuildBBSList(strIn):
	global lstBBSMsg
	global intIgnoreBBSKilled
	global blDebugFlag
	global strCallSign
	
	if (blDebugFlag):
		print ('BBS list input: ' + repr(strIn))
	del lstBBSMsg[:]
	intStart = 0
	strOut = ''
	
	while (intStart >= 0) and (intStart < len(strIn)):
		intEnd = strIn[intStart:].find('<br>')
		if intEnd < 0:
			break
		else:
			strLine = strIn[intStart:intStart+intEnd]
			#print ('Line: ' + repr(strLine))
			if (strLine == ''):
				break
			strJSON = ''
			strGroup2 = ''
			strGroup3 = ''
			strGroup4 = ''
			reObj = re.search('(\d{1,5}) {1,5} (.{6}) (.)(.) {1,5} (\d{1,5}) {1,4}(\S{4,6}) {1,5}(.{5,7}) {1,5}(\S{4,6}) {1,5}(.+)', strLine)
			if (reObj):
				#print (reObj.groups())
				try:
					datNow = date.today()
					strGroup2 = reObj.group(2)
					if (strGroup2 == datNow.strftime('%d-%b')):
						strGroup2 = 'Today'
					strGroup3 = reObj.group(3).replace('P','Pers').replace('B','Bull').replace('N','NTS')
					strGroup4 = reObj.group(4).replace('Y','Read').replace('N','Not Read/Sent').replace('F','Fwded').replace('K','Killed').replace('H','Held').replace('D','Delivered').replace('$','Pending')
					strJSON = '["' + reObj.group(1) + '", "' + strGroup2 + '", "' + strGroup3 + '", "' + strGroup4 + '", "' + reObj.group(5) + '", "' + reObj.group(6).replace(strCallSign,'Me') + '", "' + reObj.group(7).rstrip() + '", "' + reObj.group(8).replace(strCallSign,'Me') + '", "' + reObj.group(9) + '" ]'
				except:
					print('BBS JSON read error from serial')
					break
				if ((intIgnoreBBSKilled == 1) and (strGroup4 == 'Killed')):
					#ignore killed
					strJSON = ''
			if (strJSON != ''):
				lstBBSMsg.append(strJSON)
				if (strOut != ''):
					strOut = strOut + ','
				strOut = strOut + strJSON
		intStart = intStart+intEnd + 4
	# update screens with JSON
	strOut = '[ ' + strOut + ']'
	if (blDebugFlag):
		print ('BBS list output: ' + repr(strOut))
	for c in clients:
		c.write_message(HIDDEN_PREFIX + 'bbs_list' + strOut)                

def read_bbs_message(strIn):
	global blDebugFlag
	if (blDebugFlag):
		print ('BBS msg input: ' + repr(strIn))
	intStart = 0
	intEnd = 0
	strOut = ''
	# step through each line
	while (intStart >= 0) and (intStart < len(strIn)):
		intEnd = strIn[intStart:].find('<br>')
		if intEnd < 0:
			break
		else:
			strLine = strIn[intStart:intStart+intEnd+4]
			#print ('Line: ' + repr(strLine))
			if (strLine == ''):
				break
			if (strLine.find(strBBSPrompt) == -1):
				# only add if not a prompt line
				strOut = strOut + strLine
		intStart = intStart+intEnd + 4
	if (blDebugFlag):
		print ('BBS msg output: ' + repr(strOut))
	if (strOut != ''):
		for c in clients:
			c.write_message(HIDDEN_PREFIX + 'bbs_msg' + strOut)                
			
## check the serial queues for pending messages, and relay that to all connected clients
def checkQueue():
	global datCurDate
	global datLastNodeClientSend
	global datLastChatClientSend
	global datLastChatKeepAlive
	global datLastChatTyped
	global datChatBufferWaitStart
	global datLastMailCheck
	global blTrapResponse
	global blChatJoined # connected to chat
	global blChatInSwitch 
	global blNodeInSwitch 
	global blCheckChatPort
	global blChatIsAlive # chat lifesign
	global blNodeIsAlive # node lifesign
	global blChatAvailable # local user is available or not
	global blBBSCheck
	global blInBBS
	global blIgnoreChatSerial
	global blIgnoreNodeSerial
	global intChatAlertLevel # 0 = none, 1 = unfocused, 2 = 5 minutes, 3 every message
	global intUseBBS
	global intIgnoreBBSKilled
	global blChatBRFlag # whether a BR is needed before next text
	global blNodeBRFlag # whether a BR is needed before next text
	global strChatColor
	global strNodeColor
	global blDebugFlag
	global strIniFile
	global strChatLogFile
	global strChatLogRawFile
	global strNodeLogFile
	global strCallSign
	global strJSON
	global datChatBufferWaitStart
	global strChatBufferWaitFor # id owner of info we're waiting for
	global strChatBuffer
	global strHiddenBufferWaitFor
	global datHiddenBufferWaitStart
	global strHiddenBuffer
	global intHiddenPromptCount
	global intHiddenPromptsNeeded	
	global strBBSPrompt
	global blMonitorFlag
	global lstChatter
	global dicColour
	global blQueuesAlive
	global strMyChatStatus
	global datLastChatIdleCheck
	global keepRunning
	
	if (not keepRunning):
		return
		
	if not node_output_queue.empty():
		blNodeIsAlive = 1 # good lifesign
		message = node_output_queue.get()

		# Add to  log
		f = open(strNodeLogFile, "a+")
		f.write(time.strftime('%a, %b %d %Y %I:%M %p',time.localtime()) + ': ' + message)
		f.close()

		if ((message != '') and (message[0:len(message)-2] == ' ')):
			# eat the keepalive message of a single space
			message = ''
		else:
			if (blDebugFlag):
				print('From node serial:' + repr(message))
				
			#message = message.replace('<','&lt;')
			#message = message.replace('>','&gt;')
			#message = message.replace('&','&amp;')
			#message = message.replace('"','&quote;')
			#message = message.replace('\'','&apos;')
			message = message.replace('\r\n','<br>')
			# remove control characters
			message = re.sub(r'[^\x20-\x7e]', '', message)

			if (blMonitorFlag == 1):
				if ((message[2:3] == ':') and (message[5:6] == ':')) and (message[8:9] in ['T','R']):
					# colorize monitor messages
					if (message[8:9] == 'T'):
						strNodeColor = '<span style=\"color:#ff0000\">' #red
						message = strNodeColor + message 
					elif (message[8:9] == 'R'):
						strNodeColor = '<span style=\"color:#0000ff\">' #blue
						message = strNodeColor + message
					if (message[-4:] == '<br>'):
						# turn off color
						if (strNodeColor != ''):
							message = message.replace('<br>','</span><br>')
							strNodeColor = ''

			# check for state change
			if (message[-28:] == 'Enter ? for command list<br>'):
				if (blNodeInSwitch == 0):
					blNodeInSwitch = 1
					sendStateFlags('')
			elif (message[-8:] == 'cmd:<br>'):
				if (blNodeInSwitch == 1):
					blNodeInSwitch = 0
					sendStateFlags('')
				message = '' # don't show
			elif (message.find('*** DISCONNECTED<br>') >= 0):
				if (blNodeInSwitch == 1):
					blNodeInSwitch = 0
					sendStateFlags('')
			elif (message.find('*** CONNECTED to SWITCH<br>') >= 0):
				if (blNodeInSwitch == 0):
					blNodeInSwitch = 1
					sendStateFlags('')

			if (blNodeBRFlag == 1):
				message = time.strftime('%I:%M %p',time.localtime()) + ': ' + message
				blNodeBRFlag = 0
			if (message[-4:] == '<br>'):
				# set and save flag so next line causes a timestamp
				blNodeBRFlag = 1
			
			if (blDebugFlag):
				print(repr('To node web: ' + message + ' (debug)'))
				
			for c in clients:
				c.write_message(message)

	elif not hidden_output_queue.empty():
		message = hidden_output_queue.get()
		if (blDebugFlag):
			print ('From hidden:' + repr(message))
		message = message.replace('\r\n','<br>')
		# remove control characters
		message = re.sub(r'[^\x20-\x7e]', '', message)

		if (strHiddenBufferWaitFor != ''):
			if (message.find(strBBSPrompt) > -1):
				if (intHiddenPromptCount == intHiddenPromptsNeeded-1):
					# found prompt, so stop
					processHiddenBuffer()
				else:
					intHiddenPromptCount = intHiddenPromptCount + 1
			else:
				# accummulate multiple packets into buffer
				strHiddenBuffer = strHiddenBuffer + message
				#print ('Buffer bit: ' + message)

		#see if bbs info packet
		# assumes "$x unread" is in the line
		elif (message.find('unread') > 0):
			intStart = message.find(' ')
			if (message[0:intStart].isdigit()):
				strMailCount = 'mailcount>' + message[0:intStart]
				blBBSCheck = 0
				# send mailcount to screen
				for c in clients:
					c.write_message(DATA_PREFIX + strMailCount)
		elif (message == '*** DISCONNECTED<br>'):
			# try to reconnect after timeout disconnect
			hidden_input_queue.put('C SWITCH')
			#hidden_input_queue.put('BBS')
			time.sleep(1)

	elif not chat_output_queue.empty():
		message = chat_output_queue.get()
		blChatIsAlive = 1 # good lifesign
		if (blDebugFlag):
			print('From chat serial: ' + repr(message))

		# Add to raw chat log
		f = open(strChatLogRawFile, "a+")
		f.write(time.strftime('%a, %b %d %Y %I:%M %p',time.localtime()) + ': ' + message)
		f.close()
		
		if (blIgnoreChatSerial == 1):
			message = ''

		elif ((message == '') or (message[0:len(message)-2] == '') or (message[0:len(message)-2] == ' ')):
			# eat empty message
			message = ''
		elif (('Keepalive!!' in message) or (message == 'Chat Keepalive\r\n')):
			# eat the keepalive message
			message = ''
			blCheckChatPort = 0 # Turn off a possible check
			if (blDebugFlag):
				print('Ate chat keepalive at ' + time.strftime('%I:%M %p',time.localtime()) )
 
		elif (message[len(message)-len('^^TARPN Home works great!^^')-2:len(message)-2] == '^^TARPN Home works great!^^'):
			# eat the keepalive message
			message = ''
			blCheckChatPort = 0 # Turn off a possible check
			if (blDebugFlag):
				print('Ate manual keepalive at ' + time.strftime('%I:%M %p',time.localtime()))              

		else:
			#print ('In with :' + repr(message))
			strHamCall = ''
			if (message.find('Station(s) connected:\r\n') >= 0):
				# set it to buffer the entire text
				strChatBufferWaitFor = "chatlist"
				datChatBufferWaitStart = time.time()
			else:
				# find and save ham call of message
				regObj = re.search('([AWKN][A-Z]?[0-9][A-Z]{1,3})( {1,4})(.{0,15})(:|> )', message)
				if (regObj):
					strHamCall = regObj.group(1)
					if (blDebugFlag):
						print ('HamCall:>' + strHamCall + '<')
					if (regObj.lastindex > 3):
						strHamName = regObj.group(3).rstrip()
				if (((message.find(' : away\r\n') > -1) or (message.find(' : afk\r\n') > -1)) and (strHamCall != '')):
					# track away from keyboard
					for i, obj in enumerate(lstChatter):
						d = json.loads(obj)
						if ((d['Call'] == strHamCall) and (d['Status'] != 'AFK')):
							d['Time'] = time.strftime('%m-%d-%Y %H:%M',time.localtime(time.time()))
							d['Status'] = 'AFK'
							strJSON = json.dumps(d)
							lstChatter[i] = strJSON
							# update screens with JSON
							sendChatStatusUpdate(i, 'AFK', d['Time'])
							if (strHamCall == strCallSign):
								strMyChatStatus = 'AFK'
							break
				elif ((message.find(' > $TH:') > -1) and (strHamCall != '')):
					# read a partner chat status
					intTemp = message.find(' > $TH:')
					strNewStatus = message[intTemp + 7:intTemp + 10]
					strNewTime = message[intTemp + 10:].replace('\r\n','')
					for i, obj in enumerate(lstChatter):
						d = json.loads(obj)
						if (d['Call'] == strHamCall):
							d['Time'] = strNewTime
							d['Status'] = strNewStatus
							#print (strHamCall + ':' + strNewStatus + ' at ' + strNewTime + '<')
							strJSON = json.dumps(d)
							lstChatter[i] = strJSON
							# update screens with JSON
							sendChatStatusUpdate(i,strNewStatus,strNewTime)
							break
					message = '' # ignore message
				elif (strHamCall <> ''):
					# set active status
					for i, obj in enumerate(lstChatter):
						d = json.loads(obj)
						if (d['Call'] == strHamCall): 
							d['Time'] = time.strftime('%m-%d-%Y %H:%M',time.localtime(time.time()))
							strJSON = json.dumps(d)
							lstChatter[i] = strJSON
							if (d['Status'] != 'ACT'):
								d['Status'] = 'ACT'
								strJSON = json.dumps(d)
								lstChatter[i] = strJSON
								# update screens with JSON
								sendChatStatusUpdate(i,'ACT',d['Time'])
								if (strHamCall == strCallSign):
									strMyChatStatus = 'ACT'
							break 			
			# inject color coding
			strHexColor = '#000000'
			intLoc = message.find('\x1b')
			while (intLoc >= 0):
				strCode = message[intLoc+1].encode('hex')
				#print ('Code :' + strCode)
				if message[intLoc+2:intLoc+9].find(strCallSign) >= 0:
					# set local user to black
					strHexColor = '#000000'
					dicColour[strCode] = strChatColor
				elif (strCode in dicColour):
					strHexColor = dicColour[strCode]           
				else:
					for key, value in sorted(dicColour.iteritems()):
						# prefered set of colors
						if key in set(['1','2','3','4','5','6','7','8','9','10']):
							# add the new key using the old key's color
							dicColour[strCode] = value
							strHexColor = value
							# remove the numeric version
							del dicColour[key]
							break
						# only if more than 21 chatters
						if key in set(['11','12','13','14','15','16','17','18','19','20']):
							# add the new key using the old key's color
							dicColour[strCode] = value
							strHexColor = value
							# remove the numeric version
							del dicColour[key]
							break
				strChatColor = '<span style=\"color:' + strHexColor + ';font-weight:bold\">'
				#print ('Color :' + strChatColor)
				if (intLoc > 0):
					# not at first of line, inject color in the middle
					message = message[0:intLoc] + strChatColor + message[intLoc+2:]
				else:
					message = strChatColor + message[intLoc+2:]
				intEOL = message[intLoc+2:].find('\r\n')
				if ((intEOL > -1) and (strChatColor != '')):
					intEOL = intLoc+2+intEOL
					strChatColor = ''
					#print ('EOL b4 :' + message)
					message = message[0:intEOL] + '</span>' + message[intEOL:]
					#print ('EOL after :' + message)
				intLoc = message.find('\x1B')   
				 
			# make hyperlinks work
			anyURL = re.search(r'(?P<url>https?://[^\s]+)', message)
			if (anyURL):
				strURL = re.search(r'(?P<url>https?://[^\s]+)', message).group('url').replace('</span>','')
				message = message.replace(strURL,'<a href="' + strURL + '" target="_blank">' + strURL + '</a>')

			#message = message.replace('<','&lt;')
			#message = message.replace('>','&gt;')
			#message = message.replace('&','&amp;')
			#message = message.replace('"','&quote;')
			#message = message.replace('\'','&apos;')
			message = message.replace('\r\n','<br>')
			# remove control characters
			message = re.sub(r'[^\x20-\x7e]', '', message)
										
			# Track chat connection and pass state to clients
			if ((message != '') and (message[0:16] == 'Returned to Node')):
				blChatJoined = 0
				sendStateFlags('')
				message = ''

			elif ((message != '') and (message.find('[BPQChatServer-')) >= 0):
				blChatJoined = 1
				sendStateFlags('')                  
		   
			# put time stamp in front of line
			if ((blChatBRFlag == 1) and (strHamCall != '') and (message != '')):
				strCurTime = time.strftime('%I:%M %p',time.localtime()) + ': '
				intLoc = message.find(';font-weight:bold')
				if (intLoc > 0):
					# move color formatting to before the timestamp
					intStart = message.find('<span')
					if (intStart == 0):
						message = message[intStart:intLoc+19] + strCurTime + message[intLoc+19:]
				else:
					message = strCurTime + message
				blChatBRFlag = 0
			# elif (strChatColor != ''):
			#     strChatColor = ''
			#     message = '</span>' + message
			#     print('no BR but closed color span')
 
			if (message[-4:] == '<br>'):
				# set and save flag so next line causes a timestamp
				blChatBRFlag = 1
				if (strChatColor != ''):
					message = message.replace('<br>','</span><br>')
					strChatColor = ''
					print('Hit BR and closed color span')

			if (strChatBufferWaitFor != ''):
				# accummulate multiple packets into buffer
				strChatBuffer = strChatBuffer + message
				#print ('Buffer bit: ' + message)
			 
			#print('After color: ' + repr(message))
			if (message[-28:] == 'Enter ? for command list<br>'):
				if (blChatInSwitch == 0):
					blChatInSwitch = 1
					blChatJoined = 0
					sendStateFlags('')
				elif (blChatJoined == 1):
					blChatJoined = 0
					sendStateFlags('')
					if (len(lstChatter) > 0):
						del lstChatter[:]
				message = '' # don't show it
			elif (message[-8:] == 'cmd:<br>'):
				if (blChatInSwitch == 1):
					blChatInSwitch = 0
					blChatJoined = 0
					sendStateFlags('')
					if (len(lstChatter) > 0):
						del lstChatter[:]
				message = '' # don't show it
			elif (message.find('*** DISCONNECTED<br>') >= 0):
				if (blChatInSwitch == 1):
					blChatInSwitch = 0
					blChatJoined = 0
					sendStateFlags('')
					if (len(lstChatter) > 0):
						del lstChatter[:]                    
			elif (message.find('*** CONNECTED to SWITCH<br>') >= 0):
				if (blChatInSwitch == 0):
					blChatInSwitch = 1
					blChatJoined = 0
					sendStateFlags('')

			# write to the screens!
			if (message != ''):
				if (blDebugFlag):
					print(repr('To chat web: ' + message))
				for c in clients:
					c.write_message(CHAT_PREFIX + message)            

			# parse after the fact
			if ((message.find('*** Joined Chat,') > 0) and (len(lstChatter) > 0)):
				strCurColor = '#000000'
				intEndParse = message.find('<br>')
				if intEndParse > 0:
					intEndParse = intEndParse + 4
					strLine = message[0:intEndParse]

					intTemp = strLine.find('color:')
					if (intTemp > 0):
						strCurColor = strLine[intTemp + 6: intTemp+13]
						intTemp = strLine.find('>')
						if (intTemp > 0):
							strLine = strLine[intTemp+1:]
						
					intTemp = strLine.find(' : ')
					if (intTemp > 0):
						strCall = strLine[intTemp-6:intTemp].rstrip()
						# add new person if it is not me
						if (strCall != strCallSign):
							strName = strLine[intTemp + 3:strLine.find('***')-1]
							strTime = time.strftime('%m-%d-%Y %H:%M',time.localtime(time.time()))
							strJSON = json.dumps({'Name':strName, 'Call':strCall,'Color':strCurColor,'Status':'ACT','Time':strTime})
							lstChatter.append(strJSON)
							# update screens with JSON
							sendChatListToScreens()
						
							# tell the new chatter my status
							strTime = time.strftime('%m-%d-%Y %H:%M',time.localtime(datLastChatTyped))
							chat_input_queue.put('/S ' + strCall + ' $TH:' + strMyChatStatus + strTime)
			elif (message.find(' : *** Left') > -1):
				intFound = -1
				if (strHamCall != ''):
					for i, obj in enumerate(lstChatter):
						d = json.loads(obj)
						if (d['Call'] == strHamCall):
							intFound = i
							break
					if (intFound > -1):
						# remove person
						del lstChatter[i]
						# update screens with JSON
						sendChatListToScreens()

			# save chat text to pass to client when needed
			if (blChatJoined == 1):
				# save to log
				f = open(strChatLogFile, "a+")
				f.write(message.replace('<br>','\r\n'))
				f.close()

	# timed events go below here
	# ------------
	if ((strChatBufferWaitFor == 'chatlist') and (time.time() - datChatBufferWaitStart > 2)):
		# times up
		if (len(lstChatter) == 0):
			RebuildChatList(strChatBuffer)
		else:
			UpdateChatList(strChatBuffer)
		strChatBufferWaitFor = ''
		strChatBuffer = ''
			
	if ((intUseBBS == 1) and (time.time() - datLastMailCheck > 120) and (blQueuesAlive == 1)):
		# greater then 2 minutes, so check bbs unread
		blBBSCheck = 1
		try:
			if (blInBBS == 0): 
				hidden_input_queue.put('BBS')
			else:
				hidden_input_queue.put('n')		
			time.sleep(1)
			if (blInBBS == 0): 
				hidden_input_queue.put('NODE')
			time.sleep(1)
		except AssertionError:
			blQueuesAlive = 0
			blBBSCheck = 0
			print ('Hidden queue is off and disabled')

		datLastMailCheck = time.time()
	
	if ((strHiddenBufferWaitFor != '') and (time.time() - datHiddenBufferWaitStart > 7)):
		# times up
		print ('Times up: ' + strHiddenBufferWaitFor)
		processHiddenBuffer()
		
	if time.time() - datLastNodeClientSend > 1200:
		# greater then 20 minutes, so send keepalive to node port
		datLastNodeClientSend = time.time() # current time
		node_input_queue.put(' ') # just a space!
		hidden_input_queue.put(' ') # same for hidden

	if ((blChatInSwitch == 1) and (blChatJoined == 1) and (time.time() - datLastChatIdleCheck > 60)):
		# greater then 1 minute, so check and set chatter idles
		for i, obj in enumerate(lstChatter):
			d = json.loads(obj)
			datNow = time.localtime(time.time())
			datOld = time.strptime(d['Time'],'%m-%d-%Y %H:%M')
			datNow_ts = time.mktime(datNow)
			datOld_ts = time.mktime(datOld)

			# They are now in seconds, subtract and then divide by 60 to get minutes.
			intTimeDiffMinutes = int(datNow_ts-datOld_ts) / 60			
			if (d['Status'] == 'ACT'):
				if (intTimeDiffMinutes > 9):
					# 10 minute idle timeout
					d['Status'] = 'IDL'
					strJSON = json.dumps(d)
					lstChatter[i] = strJSON
					sendChatStatusUpdate(i,'IDL', d['Time'])
					if (d['Call'] == strCallSign):
						strMyChatStatus = 'IDL'
			elif (intTimeDiffMinutes > 4):
				blDoSend = False
				if ((intTimeDiffMinutes < 16) and (intTimeDiffMinutes % 5 == 0)):
					blDoSend = True # 5 mins up to 15 mins
				elif ((intTimeDiffMinutes < 61) and (intTimeDiffMinutes % 10 == 0)):
					blDoSend = True # 10 mins up to 1 hr
				elif ((intTimeDiffMinutes < 1440) and (intTimeDiffMinutes % 60 == 0)):
					blDoSend = True # on hr up to 24 hrs
				elif ((intTimeDiffMinutes > 1439) and (intTimeDiffMinutes % 1440 == 0)):
					blDoSend = True # days
				if (blDoSend):	
					sendChatStatusUpdate(i,d['Status'], d['Time'])				
		datLastChatIdleCheck = time.time() # current time
		

	if ((blChatInSwitch == 1) and (blChatJoined == 1) and (time.time() - datLastChatClientSend > 1200)):
		# greater then 20 minutes, so send keepalive to chat port
		datLastChatClientSend = time.time() # current time
		chat_input_queue.put('/S ' + strCallSign + ' Keepalive!!')
		blCheckChatPort = 1 # prep for lifesign check
	
	if ((blChatInSwitch == 1) and (blChatJoined == 1) and (time.time() - datLastChatKeepAlive > 6000)):
		# greater then 100 minutes, so send keepalive to chat port
		datLastChatClientSend = time.time() # current time
		datLastChatKeepAlive = datLastChatClientSend
		chat_input_queue.put('^^TARPN Home Keepalive!!V2.02')
		
	if ((blChatInSwitch == 1) and (blChatJoined == 1) and (blCheckChatPort == 1) and (blChatIsAlive == 1) and (time.time() - datLastChatClientSend > 60)):
		# no lifesign 1 minute after keepalive
		print ('Chat port issues at ' + time.strftime('%A, %B %d %Y',time.localtime()))
		blChatIsAlive = 0
		blCheckChatPort = 0
		sendStateFlags('')
	
# this is ready when there is time to test it
#    if datCurDate < date.today():
#        datCurDate = date.today()
#        strNewDay = time.strftime('%A, %B %d %Y',time.localtime())
#        # add day welcome to all clients
#        for c in clients:
#            c.write_message(NODE_PREFIX + 'HOME: Welcome to ' + strNewDay + '!') 
#            c.write_message(CHAT_PREFIX + 'HOME: Welcome to ' + strNewDay + '!') 
		   
	if ((keepRunning) and (not os.path.exists('remove_me_to_stop_server.txt'))):
		## file is not there, so stop the server
		keepRunning = False
		shutdownServer(WebSocketHandler)
	  
if __name__ == '__main__':
	keepRunning = True
	 
    # start the serial worker in background (as a deamon)
	try:
		sp = serialworker.SerialProcess(node_input_queue, node_output_queue, 4) ## port 4 for node commands
		sp.daemon = True
		sp.start()
	except:
		print ("Error opening /home/pi/minicom/com4. Make sure TARPN service is running.")
		keepRunning = False
	
	if (keepRunning):
		# wait a second before sending first input
		time.sleep(1)
		node_input_queue.put('conok')
		node_input_queue.put('echo on')
		node_input_queue.put('autolf on')
		node_input_queue.put('mon off') # off for now
		node_input_queue.put('c switch s')
		blNodeIsAlive = 1
		time.sleep(1)
	
		try:
			# start the chat serial worker in background (as a deamon)
			sp_chat = serialworker.SerialProcess(chat_input_queue, chat_output_queue, 6) ## port 6 for chat
			sp_chat.daemon = True
			sp_chat.start()
		except:
			print ("Error opening /home/pi/minicom/com6. Make sure TARPN service is running.")
			keepRunning = False
	if (keepRunning):
		# wait a second before sending first input
		blIgnoreChatSerial = 1
		time.sleep(1)
		chat_input_queue.put('conok')
		chat_input_queue.put('echo off')
		chat_input_queue.put('autolf on')
		chat_input_queue.put('mon off') # always off
		blIgnoreChatSerial = 0
		time.sleep(1)
		chat_input_queue.put('c switch s')
		time.sleep(1)
		blChatIsAlive = 1
		blChatInSwitch = 1
 
		# start the hidden serial worker in background (as a deamon)
		try:
			sp_hidden = serialworker.SerialProcess(hidden_input_queue, hidden_output_queue, 5) ## port 5 for hidden commands
			sp_hidden.daemon = True
			sp_hidden.start()
			blQueuesAlive = 1
			# wait a second before sending first input
			time.sleep(1)
		except:
			print ("Error opening /home/pi/minicom/com5.  Make sure TARPN service is running.")
			keepRunning = False
	
	if ((keepRunning) and (blQueuesAlive == 1)):
		try:
			hidden_input_queue.put('conok')
			hidden_input_queue.put('echo off')
			hidden_input_queue.put('autolf on')
			hidden_input_queue.put('mon off') ## always off
			hidden_input_queue.put('c switch s')
			time.sleep(1)
		except AssertionError:
			blQueuesAlive = 0
			print ('Hidden queue is off and disabled')
			keepRunning = False
	
	if ((keepRunning) and (blQueuesAlive == 1)):
		# kick off mail check
		datLastMailCheck = time.time() - 200
		
		tornado.options.parse_command_line()
			  
		app = tornado.web.Application(
			handlers=[
			  (r'/', IndexHandler),
			  (r"/upload", UploadHandler),
			  (r'/about.html', AboutHandler),
			  (r'/help.html', HelpHandler),
			  (r'/static/(.*)', tornado.web.StaticFileHandler, {'path':  './'}),
			  (r'/uploads/(.*)', tornado.web.StaticFileHandler, {'path':  './uploads'}),
			  (r'/(favicon.ico)', tornado.web.StaticFileHandler, {'path':'./'}),
			  (r'/ws', WebSocketHandler)
			] 
		)    
		httpServer = tornado.httpserver.HTTPServer(app)
		try:
			httpServer.listen(options.port)
			#print ('Listening on http port:', options.port)

			print ('Tarpn Home server is running')
		except:
			print ('Conflict opening http port ' + str(options.port))
			keepRunning = False
			
		if (keepRunning):
			#mainLoop = tornado.ioloop.IOLoop.current()
			# adjust the scheduler_interval according to the frames sent by the serial port
			scheduler_interval = 10  ## Check serial every 10 ms
			scheduler = tornado.ioloop.PeriodicCallback(checkQueue, scheduler_interval)
			scheduler.start()        
			tornado.ioloop.IOLoop.current().start()
