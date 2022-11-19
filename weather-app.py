#!/usr/bin/env python3
# A weather and clock app for "Turing Smart Screen" 3.5" IPS USB-C display
import os
import signal
import sys
import time

# Import only the modules for LCD communication
from library.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd_comm_rev_b import LcdCommRevB
from library.lcd_simulated import LcdSimulated
from library.log import logger

# import packages for clock and weather app
from datetime import datetime
import requests
import  json
import geocoder
from os.path import exists

# hard coded variables
screen_brightness = 50
api_key = "Your OpenWeatherMap API key"
# hr24 sets 24 hour clock, degc sets celsius
hr24 = False
degc = False
# d_weather = number of minutes between weather updates. default 5, minimum 2
d_weather = 5

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision: A or B (for "flagship" version, use B) or SIMU for simulated LCD (image written in screencap.png)
# To identify your revision: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "A"

def set_time():
    # get current time
    now = datetime.now()
    dt_str = now.strftime(" %m/%d/%Y")
    day_str = now.strftime('%A')
    # 24 hour or 12 hour clock
    if(hr24): tm_str = now.strftime("%H:%M:%S %p")
    else: tm_str = now.strftime("%I:%M:%S %p")
    # Display Day
    lcd_comm.DisplayText(day_str, 30, 10,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=45,
                            font_color=(255, 255, 255),
                            background_image=weather.background)
    # Display Date
    lcd_comm.DisplayText(dt_str, 230, 15,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=40,
                            font_color=(255, 255, 255),
                            background_image=weather.background)
    # Display time
    lcd_comm.DisplayText(tm_str, 170, 70,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=50,
                            font_color=(255, 255, 255),
                            background_image=weather.background)

class weather:
    # declare some common variables
    oldicon = " "
    current_temp = " "
    description = " "
    background = "res/backgrounds/dayElse.png"

    def set_location(city):
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        weather.location = city
        # url used for requests
        weather.complete_url = base_url + "appid=" + api_key + "&q=" + weather.location

    def set_weather():
        # receive weather api request
        response = requests.get(weather.complete_url)
        x = response.json()
        if x["cod"] != "404":
            # get current weather and temperature
            y = x["main"]
            z = x["weather"]
            weather.description = z[0]["description"]
            # convert temperature to C or F
            if degc:  weather.current_temp = str(round(y["temp"]-273.15,1))+"°C"
            else:  weather.current_temp = str(round(((y["temp"]-273.15)*9/5+32),1))+"°F"
            # variables for time, sunrise, and sunset
            tm = x["dt"]
            w = x["sys"]
            sunrise = w["sunrise"]
            sunset = w["sunset"]
            weather.current_weather = z[0]["main"]
            # check if it's night or day and if weather has changed for background
            if (tm > sunrise and tm < sunset):  weather.newicon = "day" +  weather.current_weather
            else:  weather.newicon = "night" +  weather.current_weather
            if  weather.newicon !=  weather.oldicon:
                weather.oldicon =  weather.newicon
                # check if background exists, else use default outlier background ie. haze, fog, mist
                weather.background = "res/backgrounds/"+ weather.newicon+".png"
                if not exists(weather.background):
                    if "day" in weather.newicon: weather.background = "res/backgrounds/dayElse.png"
                    else: weather.background = "res/backgrounds/nightElse.png"
                # display background
                lcd_comm.DisplayBitmap(weather.background)
        else:
             weather.location = "City Not Found"
        # Display location
        lcd_comm.DisplayText(weather.location, 35, 200,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=40,
                            font_color=(255, 255, 255),
                            background_image=weather.background)
        # Display custom text with solid background
        lcd_comm.DisplayText(weather.current_temp, 170, 140,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=50,
                            font_color=(255, 255, 255),
                            background_image=weather.background)
        # Display custom text with solid background
        lcd_comm.DisplayText(weather.description, 35, 250,
                            font="roboto/Roboto-Bold.ttf",
                            font_size=40,
                            font_color=(255, 255, 255),
                            background_image=weather.background)

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

    # find current location
    loc_ip = geocoder.ip('me')
    weather.set_location(loc_ip.city)

    # d_clock is typically 1 second. updates the clock at this interval
    # d_weather multiplied by 60 to convert to seconds. updates weather at this interval
    d_clock = 1
    d_weather *= 60
    # count is set to d_weather-1 so that it runs during first iteration
    count = d_weather - 1
    start_t = time.time()

    while not stop:
        # update weather if counter reaches set interval
        count += 1
        if(count==d_weather):
            weather.set_weather()
            count = 0
        # update time every loop iteration
        set_time()
        # make sure loop runs at set frequency determined by d_clock
        time.sleep(d_clock - ((time.time() - start_t) % d_clock))

    # Close serial connection at exit
    lcd_comm.closeSerial()
