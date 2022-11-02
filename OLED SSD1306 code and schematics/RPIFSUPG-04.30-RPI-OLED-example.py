import board    # This module is a container for board base pin names.
import busio     # This module supports the I2C bus protocol
import adafruit_ssd1306  # This is the display driver for SSD1306
from PIL import Image, ImageDraw, ImageFont # The&nbsp;**Python Imaging Library**&nbsp;adds image processing capabilities to your Python interpreter.

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

oled.fill(0)  # Clear the display
oled.show()

text = "Hello World!"
font = ImageFont.load_default()
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
draw.text((0,0),text,font=font,fill=255)   # coordinates (x,y) --> (horizontal, vertical)

oled.image(image)
oled.show()
