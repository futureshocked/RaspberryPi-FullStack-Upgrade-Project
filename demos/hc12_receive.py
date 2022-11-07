import board
import serial
import time

ser = serial.Serial(
            port = '/dev/ttyS0',
            baudrate = 9600,
            timeout=1.5
        )

time.sleep(2)
ser.flushInput()

print("Ctrl-C to stop")

while(True):
  line = ser.readline()
  print(line)
  
  if line:
    # Converting Byte Strings into unicode strings
    string = line.decode('utf-8', 'ignore')
    # print the string
    print("String: " + string)
    # Converting Unicode String into integer
    # To do this, remove the null and line feed characthers (\00 and \n)
    clean_string = string.replace('\00','').replace('\n','')
    try: 
       num = int(clean_string) 
       print("Converted number: " + str(num))
    except:
       print("Error...")

ser.close()

