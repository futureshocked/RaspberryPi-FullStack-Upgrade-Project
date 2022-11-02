#include "SoftwareSerial.h"

const byte HC12RxdPin = 13;                  // Recieve Pin on HC12
const byte HC12TxdPin = 14;                  // Transmit Pin on HC12

SoftwareSerial HC12(HC12TxdPin,HC12RxdPin); // Create Software Serial Port

void setup() {
  Serial.begin(9600);                       // Open serial port to computer
  Serial.println("Starting HC12...");
  HC12.begin(9600);                         // Open serial port to HC12
  Serial.println("Started HC12...");
  }

void loop() {
  if(HC12.available()){                     // If Arduino's HC12 rx buffer has data
    Serial.write(HC12.read());              // Send the data to the computer
    }
}
