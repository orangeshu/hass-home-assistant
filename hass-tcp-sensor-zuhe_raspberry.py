import os
import glob
import time
import subprocess
import socket
import struct
import threading
import Queue
import RPi.GPIO as GPIO
import spidev
import math
import binascii


GPIO.setmode(GPIO.BCM)
GPIO.setup(18,GPIO.OUT)

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0,0)

# ===updated by rocky at 2016-07-08 start===
# ===============TCP Socket Helper start=============== #

DEBUG = True

DST_SERVER_IP = '0.0.0.0'
DST_SERVER_PORT = 50556

backlog = 5
data_payload=2048
temperature = '25.68'



def get_tcp_socket():
    server_address = (DST_SERVER_IP, DST_SERVER_PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = (DST_SERVER_IP, DST_SERVER_PORT)
    #sock.connect(server_address)
    sock.bind(server_address)
    sock.listen(backlog)
    return sock



class Producer(threading.Thread):
	def __init__(self,threadname):
	   threading.Thread.__init__(self,name=threadname)
	   
	def run(self):
		global pm25
		DST_SERVER_IP = '115.28.150.131'
		DST_SERVER_PORT = 20199
		packer = struct.Struct('!H H f')
		
		def get_tcp_socket():
			server_address = (DST_SERVER_IP, DST_SERVER_PORT)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			sock.connect(server_address)
			return sock
			
		def send_data2server(data):
			sock = None
			try:
				sock = get_tcp_socket()
				packed_data = packer.pack(*data)
				sock.sendall(packed_data)
				if DEBUG:
					print('Succeed in sending "{} {}" to {}'.
				      format(binascii.hexlify(packed_data), data, sock.getpeername()))
			except Exception as e:
				print('Error:', e)
			finally:
				if sock:
					sock.close()
			
		CHECK_INTERVAL = 1
		DEVICE_ID = 1
		SENSOR_ID = 3
		def ReadChannel(channel):
			adc = spi.xfer2([1,(8+channel)<<4,0])
			data = ((adc[1]&3) << 8) + adc[2]
			return data
		
		# Function to calculate temperature from
        # TMP36 data, rounded to specified
        # number of decimal places.		
		
		def ConvertSharp(data,places):
			sharp = ((data * 3.3)/float(1023))
			sharp = round(sharp,places)
			return sharp
			
		# Define sensor channels
        #light_channel = 0
		sharp_channel  = 4
		i=0
		sum_volts=0
		sum_level=0
		base_volts=56.7
		
		
		while True:
			GPIO.output(18,True)
			time.sleep(0.00028)
			
			sharp_level = ReadChannel(sharp_channel)
			sharp_volts = ConvertSharp(sharp_level,2)
			
			GPIO.output(18,False)
			time.sleep(0.00968)
			
			sum_volts=sum_volts+sharp_volts
			sum_level=sum_level+sharp_level
			i+=1
			if i > 2998:
				average_volts = sum_volts/i
				average_level = sum_level/i
				pm25 = 378*average_volts-base_volts
				i=0
				sum_level=0
				sum_volts=0	
				data = (DEVICE_ID , SENSOR_ID,pm25)
				send_data2server(data)
				print(('the pm2.5 is %f' %pm25))
				print "--------------------------------------------"  
				print("Sharp  : {} ({}V)".format(average_level,average_volts)) 
				return pm25

		
	
class Send(threading.Thread):
	def __init__(self,threadname):
	   threading.Thread.__init__(self,name=threadname)
	global client
	def run(self):
	   try:
		  sock = get_tcp_socket()
		  print 'Waiting to receiving message from client'
		  client, address = sock.accept()
		  data_from_hass = client.recv(data_payload)
		  if data_from_hass:
			 print 'Receive Data: %s ' % data_from_hass
			 pm_25=str(pm25)
			 client.send(pm_25)
			 print 'Sent: %s back to %s' % (pm_25, address)
	   except Exception as e:
			print('Error:', e)
	   finally:
		   client.close()
		   
		   



def test():
	listthread=[]
	
	thread1 = Producer(1)
	listthread.append(thread1)
	
	thread2= Send(2) 
	listthread.append(thread2)
	
	for threadnumber in listthread:
		threadnumber.start()
	
if __name__=='__main__':
	while True:
		test()
		time.sleep(31)

