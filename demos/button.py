import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel):
        print("Button was pushed!")

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set GPIO 14 / pin 8 to be an input pin and set initial value to be pulled low (off)

GPIO.add_event_detect(15,GPIO.RISING,callback=button_callback) # Setup event on GPIO 14 / pin 8 rising edge

message = input("Press enter to quit") # Run until someone presses enter

GPIO.cleanup() # Clean up

