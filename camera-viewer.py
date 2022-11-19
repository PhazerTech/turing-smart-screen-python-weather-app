#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import signal
import sys
from datetime import datetime
import cv2
import io

# Import only the modules for LCD communication
from library.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd_comm_rev_b import LcdCommRevB
from library.lcd_simulated import LcdSimulated
from library.log import logger

# hard coded variables
screen_brightness = 50
# default is set for USB webcam
cam_feed = cv2.VideoCapture(1)

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision: A or B (for "flagship" version, use B) or SIMU for simulated LCD (image written in screencap.png)
# To identify your revision: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "A"

stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True

    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Build your LcdComm object based on the HW revision
    lcd_comm = None
    if REVISION == "A":
        logger.info("Selected Hardware Revision A (Turing Smart Screen)")
        lcd_comm = LcdCommRevA(com_port="AUTO",
                               display_width=320,
                               display_height=480)
    elif REVISION == "B":
        print("Selected Hardware Revision B (XuanFang screen version B / flagship)")
        lcd_comm = LcdCommRevB(com_port="AUTO",
                               display_width=320,
                               display_height=480)
    elif REVISION == "SIMU":
        print("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=320,
                                display_height=480)
    else:
        print("ERROR: Unknown revision")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    # Reset screen in case it was in an unstable state (screen is also cleared)
    lcd_comm.Reset()

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: screen can get very hot at high brightness!)
    lcd_comm.SetBrightness(level=screen_brightness)

    # Set backplate RGB LED color (for supported HW only)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))

    # Set orientation (screen starts in Portrait)
    orientation = Orientation.LANDSCAPE
    lcd_comm.SetOrientation(orientation=orientation)

    # count will make sure to only process 1 frame for every 15, or 2 fps
    count = 0
    while not stop:
        ret, img = cam_feed.read()
        count += 1
        if(count == 15):
            img2 = cv2.resize(img, (480,320))
            is_success, buffer = cv2.imencode(".png", img2)
            io_buf = io.BytesIO(buffer)
            lcd_comm.DisplayBitmap(io_buf)
            count = 0

    # Close serial connection at exit
    cam_feed.release()
    lcd_comm.closeSerial()
