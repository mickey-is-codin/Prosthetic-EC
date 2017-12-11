import pyglet
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import socket
import threading
import sys
import os

#Un-comment this if using OS-X.
os.system('defaults write org.python.python ApplePersistenceIgnoreState NO')

WindowSize = 5000
SampleRate = 1000.0
VoltsPerBit = 2.5/256

#Define global variables
Fs = 1000                                         #Fs is the sample frequency likely in Hz. So we have 1kHz = the sampling frequency.
                                                  #By the Nyquist theorem we know that the max frequency = 0.5 * Fs so max F = 500Hz for this system. Makes sense for EMG.
FlexWindowSize = 0.25
data = []                                         #The array that will hold all of the data that we are plotting using matplotlib. This is our y array.
displayData = [-2 for i in range(WindowSize)]     #Data that only appears in the window size
frame = 0
threshold = 0
mickeyWindow = np.zeros(400)
squares = np.zeros(len(mickeyWindow))
mickeyWindowList = []
squaresList = []
flexing = False                                   #Initialize this to false so that it does not assume that we are immediately flexing.

# This reads from a socket.
def data_listener():                              #Data listener definition: Anything that is able to "listen" for incoming data from a control. Usually an object outside of the program. In our instance the Control is the EMG signal coming from our arm.
  global data
  UDP_PORT = 9000
  sock = socket.socket(socket.AF_INET, # Internet
                      socket.SOCK_DGRAM) # UDP
  sock.bind((UDP_IP, UDP_PORT))
  while True:                                     #While True is python's way of doing an update function. It evaluates over and over again at Python's frame rate.
    newdata, addr = sock.recvfrom(1024) # buffer size is 1024 bytes.------
    data.extend(list(newdata))                    #Adds all of the list of the new data to the original data array.

#Handle command line arguments to get IP address
if (len(sys.argv) == 2):
    try:
        UDP_IP = sys.argv[1]
        socket.inet_aton(UDP_IP)
    except:
        sys.exit('Invalid IP address, Try again')
else:
    sys.exit('EMG_Acquire <Target IP Address>')

#Connect the UDP_Port
UDP_PORT = 9000
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP

print('Connected to ', str(UDP_IP))
print("Listening for incoming messages...")
print('Close Window to exit')

#Start a new thread to listen for data over UDP
thread = threading.Thread(target=data_listener)     #Thread is potentially similar to a coroutine?
thread.daemon = True                                #.daemon => A thread that's closed at shutdown. The entire python program exits when only daemon threads are left.
thread.start()

#Load and place image resources
pyglet.resource.path = ['./resources']              #Pyglet allows for GUI creation within a python program. This set of instructions will probably set images.
pyglet.resource.reindex()                           #We set the path where the resources exist above (file holding the images) here we reindex it
ForeArm_image = pyglet.resource.image("forearm.png")#Set an image in that path we set above and grab the appropriate name.
Bicep_image = pyglet.resource.image("Bicep.png")    #Same as the function above but for the bicep
ForeArm_image.anchor_x = 7                          #Set the x anchor to be 7
ForeArm_image.anchor_y = ForeArm_image.height-150   #Set the y anchor to be the full height of the image - 150 px? 
Bicep_image.anchor_x = Bicep_image.width/2          #Set the x anchor to be half of the image
Bicep_image.anchor_y = Bicep_image.height/2         #Set the y anchor to be half of the height. The bicep is centered at the center of the screen.

#Define the moving ForeArm class
class ForeArm(pyglet.sprite.Sprite):
  def __init__(self, *args, **kwargs):
    super(ForeArm,self).__init__(img=ForeArm_image,*args, **kwargs)	
    self.rotate_speed = 150.0
    self.rotation_upper_limit = -10
    self.rotation_lower_limit = -100
    self.rotation = self.rotation_upper_limit
    self.key_handler = pyglet.window.key.KeyStateHandler()

  def update(self, dt):
    if flexing:
      if not ((self.rotation-self.rotate_speed*dt) <=  self.rotation_lower_limit):
        self.rotation -= self.rotate_speed*dt
      else:
        self.rotation = self.rotation_lower_limit
    else:
      if not((self.rotation+self.rotate_speed*dt) >= self.rotation_upper_limit):
        self.rotation += self.rotate_speed*dt
      else:
        self.rotation = self.rotation_upper_limit


#Setup the main window
#Dan notes for windowing
main_window = pyglet.window.Window(1000,600)
main_batch = pyglet.graphics.Batch()
background = pyglet.graphics.OrderedGroup(0)
foreground = pyglet.graphics.OrderedGroup(1)
bicep = pyglet.sprite.Sprite(img=Bicep_image,x=350,y=150,batch=main_batch,group=background)
forearm = ForeArm(x=510, y=115,batch=main_batch,group=foreground)
pyglet.gl.glClearColor(1, 1, 1, 1)
main_window.push_handlers(forearm)
main_window.push_handlers(forearm.key_handler)


def update(dt):
  #Refresh rate of 60 times per second. This updates the animation.
  #Grabs new data and creates a new display and updates that with newdata
  #Plot

  #Don't look at newData, look at display data after it's been updated.
  #Displaydata is more important. Look at a subset of displayedData.
  #Look at newest whatever second of data. 
  #Display data is always the latest 5,000 data points or 5 seconds of data.

  global displayData, data, flexing, frame, threshold, mickeyWindow

  newData = list(data)
  data = []
  newDisplay = list(displayData[len(newData):len(displayData)] + newData)
  displayData = list(newDisplay)

  #EVERY UPDATE WE'RE PASSED ALL OF THE FLEX INFORMATION THAT HAS OCCURRED BETWEEN UPDATES
  #newData's first length is 530

  #Mickey Code Start

  #Oct 30th Code"

  mickeyWindowList = [(displayData[i + len(displayData) - len(mickeyWindow)] - 128.0) for i in range(0,len(mickeyWindow))]
  squaresList = [(mickeyWindowList[i])**2 for i in range(0,len(mickeyWindow))]

  rmsMickey = (sum(squaresList) / float(len(mickeyWindowList))) ** 0.5   #Calculate rms of whole mickeyWindow for most recent 100
  
  if frame >= 19:       
    if frame == 20: #On the 10th frame you take the rms of my window and set it as the threshold
      threshold = rmsMickey * 1.6 #1.6 times the RMS value of the most recent noise floor is our threshold.
      print(threshold)

    #Trying to see if rms of most recent 100 goes above the rms set from the first 10 frames

    if (rmsMickey > threshold) & (threshold > 0): 
      flexing = True
    else:
      flexing = False     #END RMS Calculations

  frame = frame + 1

  #Mickey Code End

  forearm.update(dt)

@main_window.event
def on_draw():
    main_window.clear()
    main_batch.draw()

pyglet.clock.schedule_interval(update, 1/120.0)
pyglet.app.run()