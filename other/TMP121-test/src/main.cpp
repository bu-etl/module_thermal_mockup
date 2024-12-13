#include <SPI.h>
#include <Arduino.h>

#define PIN_DOUT 0
#define PIN_CLK 2
#define PIN_CS 10

/* ----------------------------------------------------- 
  SPI Functions
----------------------------------------------------- */
void clk() {
  delayMicroseconds(100);
  digitalWrite(PIN_CLK, HIGH);
  delayMicroseconds(100);
  digitalWrite(PIN_CLK, LOW);
}

unsigned long readSPI(uint8_t size_bits) {
  //Serial.println("Reading SPI");
  //Serial.println("Size Bits: " + String(size_bits));
  unsigned long value = 0;
  for (int i = size_bits - 1; i >= 0; i--) {
    //Serial.println("Reading bit " + String(i));
    if (digitalRead(PIN_DOUT)) {
      value |= (1 << i);
    }
    clk();
  }
  return value;
}

void readTemperature(){
  delay(320);
  digitalWrite(PIN_CS, LOW);
  unsigned long rawValue = readSPI(16);
  digitalWrite(PIN_CS, HIGH);
  Serial.println("Temp Probe: 0x" + String(rawValue, HEX));
  rawValue >>= 3;

  if (rawValue & 0x1000) {
    rawValue |= 0xE000;  // Sign extend to 16 bits if the temperature is negative
  }

  Serial.print("Processed Temperature Data: ");
  Serial.println(rawValue);
  float temperatureC = rawValue * 0.0625;
  
  Serial.print("Temperature: ");
  Serial.print(temperatureC);
  Serial.println(" °C");
  delay(1000);
}


/* ----------------------------------------------------- 
  Setup 
----------------------------------------------------- */
void setup() {
  Serial.begin(9600);
  pinMode(PIN_DOUT, INPUT);
  pinMode(PIN_CLK, OUTPUT);
  pinMode(PIN_CS, OUTPUT);
  digitalWrite(PIN_CS, HIGH);  
  Serial.println("Setup complete, starting temperature read...");
}

void loop() {
  readTemperature();
}


/* ----------------------------------------------------- 
  TMP121 Code using build in SPI Library
----------------------------------------------------- */
/*
const int chipSelectPin = 10;

int16_t readTemperature();

void setup() {
  Serial.begin(9600);

  pinMode(chipSelectPin, OUTPUT);
  digitalWrite(chipSelectPin, HIGH); 

  SPI.begin();
  SPI.setDataMode(SPI_MODE0);  // Clock idle low, data valid on rising edge
  SPI.setClockDivider(SPI_CLOCK_DIV8);
  SPI.setBitOrder(MSBFIRST);   

  Serial.println("Setup complete, starting temperature read...");
}

void loop() {
  int16_t temperature = readTemperature();
  
  float temperatureC = temperature * 0.0625;
  
  Serial.print("Temperature: ");
  Serial.print(temperatureC);
  Serial.println(" °C");
  
  delay(1000);
}

int16_t readTemperature() {
  int16_t temp;

  delay(320);
  digitalWrite(chipSelectPin, LOW);

  uint8_t highByte = SPI.transfer(0x00);
  uint8_t lowByte = SPI.transfer(0x00);

  digitalWrite(chipSelectPin, HIGH);

  temp = (highByte << 8) | lowByte;
  
  Serial.print("Raw High Byte: ");
  Serial.print(highByte, BIN);
  Serial.print(" Low Byte: ");
  Serial.println(lowByte, BIN);

  // Shift right by 3 to remove the 3 least significant bits (TMP121 returns 13-bit data)
  temp >>= 3;

  // Handle negative temperatures (12-bit two's complement format)
  if (temp & 0x1000) {
    temp |= 0xE000;  // Sign extend to 16 bits if the temperature is negative
  }

  Serial.print("Processed Temperature Data: ");
  Serial.println(temp);

  return temp;
}
*/