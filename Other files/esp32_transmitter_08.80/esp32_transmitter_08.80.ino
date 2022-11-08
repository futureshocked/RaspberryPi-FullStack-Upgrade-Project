#include "SoftwareSerial.h"
#include <BME280I2C.h>
#include <Wire.h>

BME280I2C bme;

char this_device_id = '3';

const byte HC12RxdPin = 13;  // Recieve Pin on HC12
const byte HC12TxdPin = 14;  // Transmit Pin on HC12
                             // Do not use GPIO12: https://github.com/espressif/esp-idf/tree/release/v3.2/examples/storage/sd_card#note-about-gpio12

float temp(NAN), hum(NAN), pres(NAN);

const byte verify_pin = 32; // Use this pin to drive a status indicator LED. Eventually, this
                            // LED will light up when a valid transmission is confirmed.
                            // For now, it will just light up when a transmission happens.

hw_timer_t *Transmit_timer = NULL;
hw_timer_t *LED_off_timer = NULL;
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;

SoftwareSerial HC12(HC12TxdPin, HC12RxdPin);  // Create Software Serial Port

unsigned long millis_to_tx;

unsigned long millis_to_sensor_measurement = 5000; 
unsigned long previous_measurement_millis = 0;  // will store last time LED was updated

String message;

char message_buffer[70];
char last_message_sent[70];

void IRAM_ATTR onTransmitTimer() {

  portENTER_CRITICAL_ISR(&timerMux);  // Enter critical section of the interrupt routine. Disable timer.

  //Can't use I2C inside the critical section, got to get sensor readings in the loop.
  digitalWrite(verify_pin, HIGH); // Turn on the LED
  HC12.write(message_buffer, message.length());
  strcpy(last_message_sent, message_buffer);  //Make a copy of the message so we can verify receipt.
  digitalWrite(verify_pin, LOW);
  portEXIT_CRITICAL_ISR(&timerMux);  // Exit critical section of the interrupt routine. Enable timer.
}

void setup() {
  pinMode(verify_pin, OUTPUT);
  Serial.begin(9600);  // Open serial port to computer
  Serial.println("Starting HC12 module.");
  HC12.begin(9600);  // Open serial port to HC12
  delay(1000);
  if (!HC12) {  // If the object did not initialize, then its configuration is invalid
    Serial.println("Invalid SoftwareSerial pin configuration, check config");
    while (1) {  // Don't continue with invalid configuration
      delay(1000);
    }
  }
  Serial.println("Started HC12 module.");

  // Start BME280
  Wire.begin();

  while (!bme.begin()) {
    Serial.println("Could not find BME280 sensor!");
    delay(1000);
  }

  switch (bme.chipModel()) {
    case BME280::ChipModel_BME280:
      Serial.println("Found BME280 sensor! Success.");
      break;
    case BME280::ChipModel_BMP280:
      Serial.println("Found BMP280 sensor! No Humidity available.");
      break;
    default:
      Serial.println("Found UNKNOWN sensor! Error!");
  }

  delay(1000);

  digitalWrite(verify_pin, LOW);

  // Setup the HC12 message receive timer
  Transmit_timer = timerBegin(0, 80, true);
  timerAttachInterrupt(Transmit_timer, &onTransmitTimer, true);
  int tx_period_in_seconds = 30; //Easier to work in seconds rather that microseconds
                                  // 10 minutes is 60*10 = 600 seconds                                  

  timerAlarmWrite(Transmit_timer, tx_period_in_seconds * 1000000, true);
                                  // Don't transmit too often because the Rpi needs time to log to the GSheet.
                                  // 10 seconds or larger period is Ok.
  timerAlarmEnable(Transmit_timer);  //Just Enable

}

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previous_measurement_millis > millis_to_sensor_measurement) {
    previous_measurement_millis = currentMillis;
    take_sensor_reading_and_prep_message();
  }
}

void take_sensor_reading_and_prep_message() {
  unsigned long millis_message_stamp = millis();
  temp    = bme.temp();
  hum      = bme.hum();
  pres      = bme.pres();
  message = String(millis_message_stamp) + "," + String(temp, 2) + "," + String(hum, 2) + "," + String(pres, 2) + "," + String(this_device_id) + ",999";  // ! is the end character
  message.toCharArray(message_buffer, message.length() + 1);      // Must add one to the String length, otherwise last character is lost.
  Serial.print("New reading: ");
  Serial.println(message);
}