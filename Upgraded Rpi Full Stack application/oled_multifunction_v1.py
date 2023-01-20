import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
import os
import sqlite3
from ischedule import schedule, run_loop  #https://pypi.org/project/ischedule/
import signal

button_press = 1  # Keep track of button presses. Use this variable to cycle through display pages.
                  # Start with free space.

# The display can accomodate four lines
line1 = ""
line2 = ""
line3 = ""
line4 = ""

screen_pages = ["1", "3"] # This array holds the sensor ID (numeral) or function code (S for "disk Space").

led_pin = 4  # Use this LED to convey useful info to the user. For example, it can toggle when OLED is refreshed.
button_pin = 22 # GPIO 22 (BCM) = Pin 15 (physical) 
#GPIO.setmode(GPIO.BOARD)
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin, GPIO.LOW)

# Prepare the I2C OLED display
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)
font = ImageFont.truetype("/var/www/lab_app/fonts/arial.ttf",18)

def handler(signum, frame):
    res = input("Ctrl-c was pressed. Do you really want to exit? y/n ")
    if res == 'y':
        GPIO.cleanup()
        exit(1)

# this is the event handler for the button press
def button_callback(channel):
        global button_press #Without global, Python gets confused when assigning a new value.
                            # for some reason, Python "thinks" that button_press is a local variable.
        time.sleep(0.05) # edge debounce of 5mSec
        print("Button pressed")
        if GPIO.input(channel) == 1:    
            print("--------------")
            print("Button was pressed")
            button_press += 1
            if button_press < len(screen_pages):
               pass
            else:
               button_press = 0
        print("button_press: " + str(button_press) + ", screen_pages: " + str(screen_pages[button_press]) + ", screens:" + str(len(screen_pages)))
        write_to_oled()
        return

# This function writes to the screen
def write_to_oled():
    GPIO.output(led_pin, GPIO.HIGH)
    # get_data_from_database()
    oled.fill(0)
    oled.show()
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    display_parts = [] # This array will hold the text for the four display lines
    print("button_press: " + str(button_press) + ", screen_pages: " + str(screen_pages[button_press]))
    display_parts = get_database_records(screen_pages[button_press])
    
    print(display_parts)
    line1 = display_parts[0]
    line2 = display_parts[1] # + " °C"
    line3 = display_parts[2] # + " %"
    line4 = display_parts[3] # + " Pa"
    
    draw.text((5, 0), line1, font=font,fill=255)
    draw.text((5, 15), line2, font=font,fill=255)
    draw.text((5, 30), line3, font=font,fill=255)
    draw.text((5, 45), line4, font=font,fill=255)
    draw.text((115,45), str(screen_pages[button_press]), font=font,fill=255)
    oled.image(image)
    oled.show()
    GPIO.output(led_pin, GPIO.LOW)

def get_database_records(sensor_id):
    temperature = "-99"
    humidity    = "-99"
    pressure    = "-99"

    conn=sqlite3.connect('/var/www/lab_app/lab_app.db')
    curs=conn.cursor()
    # Get the temperature
    sql = "SELECT * FROM temperatures WHERE sensorID = " + str(sensor_id) + " ORDER BY rDatetime DESC LIMIT 1"
    #print(sql)
    curs.execute(sql)
    row = curs.fetchone()
    if row[2] is not None:
       temperature = str(round(row[2],2))
    date_time = row[0]

    # Get the humidity
    sql = "SELECT * FROM humidities WHERE sensorID = " + str(sensor_id) + " ORDER BY rDatetime DESC LIMIT 1"
    #print(sql)
    curs.execute(sql)
    row = curs.fetchone()
    if row[2] is not None:
       humidity = str(round(row[2],2))

    # Get the pressure
    sql = "SELECT * FROM pressures WHERE sensorID = " + str(sensor_id) + " ORDER BY rDatetime DESC LIMIT 1"
    curs.execute(sql)
    row = curs.fetchone()
    if row is not None: 
       pressure = str(round(row[2],2))

    conn.close()
    
    record_date_time = datetime.fromisoformat(date_time).strftime('%d/%m/%y %H:%M')
    line1 = record_date_time
    line2 = temperature + " °C"
    line3 = humidity + " %"
    line4 = pressure + " hPa"
    return [line1 , line2, line3, line4]

def update_oled():
    print("Updating OLED")
    write_to_oled()

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set GPIO 14 / pin 8 to be an input pin and set initial value to be pulled low (off)

# These two event handlers must be defined after the handler functions
signal.signal(signal.SIGINT, handler)  # This will capture a Ctrl-C and call a handler function
GPIO.add_event_detect(button_pin,GPIO.RISING,callback=button_callback) # Setup event on GPIO 14 / pin 8 rising edge

schedule(update_oled, interval=60.0)

print("Ready")

write_to_oled()

run_loop()

