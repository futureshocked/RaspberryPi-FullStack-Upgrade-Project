#include "SoftwareSerial.h"

const byte HC12RxdPin = 13;                  // Recieve Pin on HC12
const byte HC12TxdPin = 14;                  // Transmit Pin on HC12

SoftwareSerial HC12(HC12TxdPin,HC12RxdPin); // Create Software Serial Port

unsigned long millis_to_tx;

char buf[20];

void setup() {
  Serial.begin(9600);                       // Open serial port to computer
  Serial.println("Starting HC12 module.");
  HC12.begin(9600);                         // Open serial port to HC12
  Serial.println("Started HC12 module.");
}

void loop() {
  millis_to_tx = millis();

  utoa(millis_to_tx,buf,10); // Convert an unsigned long to a char array. Beware of itoa which is better for int.
  Serial.print(millis_to_tx);
  Serial.print(" --> ");
  HC12.write(buf, sizeof(buf));
  Serial.write(buf, sizeof(buf));

  HC12.write(10);  // Send a LF. A CR is 13
  Serial.println();

  delay(1000);
}
