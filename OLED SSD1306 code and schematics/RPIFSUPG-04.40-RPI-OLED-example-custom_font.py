# Get the required font from https://fonts101.com/download/79423/Arial/6E7385FB7D6CEDDF07B5A41E0BC2712D

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

oled.fill(0)  # Clear the display
oled.show()

text1 = "Hello"
text2 = "World!"
font1 = ImageFont.truetype("arial.ttf", 15)
font2 = ImageFont.truetype("arial.ttf", 20)
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
draw.text((0,0),text1,font=font1,fill=255)     # coordinates (x,y) --> (horizontal, vertical)
draw.text((0,20),text2,font=font2,fill=255)   # coordinates (x,y) --> (horizontal, vertical)

oled.image(image)
oled.show()
