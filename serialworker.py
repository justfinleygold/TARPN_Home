import serial
import time
import multiprocessing

SERIAL_PORT = '/home/pi/minicom/com'
SERIAL_BAUDRATE = 19200
keepRunning = True

class SerialProcess(multiprocessing.Process):

    def __init__(self, input_queue, output_queue, portNum):
        multiprocessing.Process.__init__(self)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.sp = serial.Serial(SERIAL_PORT + str(portNum), SERIAL_BAUDRATE, timeout=1)
        
    def close(self):
        keepRunning = False
        time.sleep(2)
        self.sp.close()
        ##print ("Worker closed")
        
    def writeSerial(self, data):
        self.sp.write(data.encode())
        time.sleep(1) 
        
    def readSerial(self):
        return self.sp.readline()
 
    def run(self):
        #print ("Serial run")
        self.sp.flushInput()
        while keepRunning:
            # look for incoming tornado request
            if not self.input_queue.empty():
                data = self.input_queue.get()
                # send it to the serial device
                ##print ("Writing to serial: " + data)
                self.writeSerial(data + "\r")
	    else:
                time.sleep(0.01)
  
            # look for incoming serial data
            if (self.sp.inWaiting() > 0):
                data = self.readSerial()
                ##print ("Reading from serial: " + data)
                # send it back to tornado
                self.output_queue.put(data)
            else:
                time.sleep(0.01)

