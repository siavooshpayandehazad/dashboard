# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import time
import subprocess
import sched, time

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from datetime import datetime
from gpiozero import CPUTemperature

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -25
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
#font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype('font.ttf', 88)
font2 = ImageFont.truetype('font.ttf', 48)
counter = 0
counterThreshold = 30

def writeOnScreen(sc):
    global counter
    disp.fill(0)
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    if counter > counterThreshold:
        # Write four lines of text.
        draw.text((x, top+0),  datetime.now().strftime('%H:%M:%S') , font=font, fill=255)
    else:
        cpuTemp = CPUTemperature()
        draw.text((x, -15),  "CPU TEMP: " , font=font2, fill=255)
        draw.text((x, 2),  "%.1f" %cpuTemp.temperature + "°C" , font=font2, fill=255)
    # Display image.
    disp.image(image)
    disp.show()
    counter += 1
    if counter == 2*counterThreshold:
        counter = 0
    s.enter(0.2, 1, writeOnScreen, (sc,))


s = sched.scheduler(time.time, time.sleep)
s.enter(0.2, 1, writeOnScreen, (s,))
s.run()
