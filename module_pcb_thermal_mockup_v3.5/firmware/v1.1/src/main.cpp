#include <Arduino.h>
// For some reason the compiler needs Command in a header file :|
#include "command.h"

// Pin Assignments
#define PIN_CLK 2
#define PIN_DIN 1
#define PIN_DOUT 0
#define PIN_RDYB 5
#define PIN_CSB 3
#define PIN_RSTB 4
#define PIN_PROBE_1_CSB 6
#define PIN_PROBE_2_CSB 7
#define PIN_PROBE_3_CSB 8

// Bits for ADC
#define ADC_BITS_AD7718 24
#define ADC_BITS_AD7708 16

// Register Addresses
#define REG_STATUS 0x0
#define REG_MODE 0x1
#define REG_ADC_CONTROL 0x2
#define REG_FILTER 0x3
#define REG_ADC_DATA 0x4
#define REG_ADC_OFFSET 0x5
#define REG_ADC_GAIN 0x6
#define REG_IO_CONTROL 0x7
#define REG_TEST_1 0xC
#define REG_TEST_2 0xD
#define REG_ID 0xF

// Status Register Flags
#define STATUS_RDY 0x80
#define STATUS_CAL 0x20
#define STATUS_ERR 0x08
#define STATUS_LOCK 0x01

// ADC Control Register Flags
#define ADC_CONTROL_RANGE_20mV        0x00
#define ADC_CONTROL_RANGE_40mV        0x01
#define ADC_CONTROL_RANGE_80mV        0x02
#define ADC_CONTROL_RANGE_160mV       0x03
#define ADC_CONTROL_RANGE_320mV       0x04
#define ADC_CONTROL_RANGE_640mV       0x05
#define ADC_CONTROL_RANGE_1p28V       0x06
#define ADC_CONTROL_RANGE_2p56V       0x07
#define ADC_CONTROL_UNIPOLAR_ENCODING 0x08

#define ADC_CONTROL_AIN1_PSEUDODIFFERENTIAL 0x00
#define ADC_CONTROL_AIN2_PSEUDODIFFERENTIAL 0x10
#define ADC_CONTROL_AIN3_PSEUDODIFFERENTIAL 0x20
#define ADC_CONTROL_AIN4_PSEUDODIFFERENTIAL 0x30
#define ADC_CONTROL_AIN5_PSEUDODIFFERENTIAL 0x40
#define ADC_CONTROL_AIN6_PSEUDODIFFERENTIAL 0x50
#define ADC_CONTROL_AIN7_PSEUDODIFFERENTIAL 0x60
#define ADC_CONTROL_AIN8_PSEUDODIFFERENTIAL 0x70
#define ADC_CONTROL_AIN1_DIFFERENTIAL       0x80
#define ADC_CONTROL_AIN3_DIFFERENTIAL       0x90
#define ADC_CONTROL_AIN5_DIFFERENTIAL       0xA0
#define ADC_CONTROL_AIN7_DIFFERENTIAL       0xB0

// Mode Register Flags
#define MODE_CHOPB 0x80
#define MODE_NEGBUF 0x40
#define MODE_REFSEL 0x20
#define MODE_CHCON 0x10
#define MODE_OSCPD 0x08
#define MODE_IDLE 0x01
#define MODE_SINGLE_CONVERSION 0x02
#define MODE_CONTINUOUS_CONVERSION 0x03
#define MODE_ZERO_SCALE_CALIBRATION 0x04
#define MODE_FULL_SCALE_CALIBRATION 0x05
#define MODE_SYSTEM_ZERO_SCALE_CALIBRATION 0x06
#define MODE_SYSTEM_FULL_SCALE_CALIBRATION 0x07

const int cs_pins[4] = {PIN_CSB, PIN_PROBE_1_CSB, PIN_PROBE_2_CSB, PIN_PROBE_3_CSB};


/* ----------------------------------------------------- 
  Parsing Functions
----------------------------------------------------- */
unsigned char hex2char(String s) {
  if (s.length() < 2) {
    Serial.println("ERROR: Bad Hex conversion, must be two characters");
    return 0;
  }
  unsigned char out = 0;
  for (int i=0; i<2; i++) {
    out = out << 4;
    char current = s.charAt(i);
    switch (current) {
      case '0': out = out | 0x0; break;
      case '1': out = out | 0x1; break;
      case '2': out = out | 0x2; break;
      case '3': out = out | 0x3; break;
      case '4': out = out | 0x4; break;
      case '5': out = out | 0x5; break;
      case '6': out = out | 0x6; break;
      case '7': out = out | 0x7; break;
      case '8': out = out | 0x8; break;
      case '9': out = out | 0x9; break;
      case 'A': out = out | 0xA; break;
      case 'B': out = out | 0xB; break;
      case 'C': out = out | 0xC; break;
      case 'D': out = out | 0xD; break;
      case 'E': out = out | 0xE; break;
      case 'F': out = out | 0xF; break;
    }
  }
  return out;
}

Command parse_command(String line) {
  Command command;
  command.nargs = 0;
  int split;
  line.trim();

  split = line.indexOf(' ');
  if (split < 0) split = line.length();
  command.cmd = line.substring(0, split);
  line = line.substring(split);
  line.trim();
  // Serial.printf("Command: %s\n", command.cmd.c_str());

  while(line.length() > 0 && command.nargs < MAX_ARGS) {
    split = line.indexOf(' ');
    if (split < 0) split = line.length();
    command.args[command.nargs] = line.substring(0, split);
    command.args[command.nargs].trim();
    // Serial.printf("Argument %d: '%s'",command.nargs, command.args[command.nargs].c_str());
    command.nargs++;
    line = line.substring(split);
    line.trim();
  }
  return command;
}


/* ----------------------------------------------------- 
  SPI Functions
----------------------------------------------------- */
void clk() {
  delayMicroseconds(100);
  digitalWrite(PIN_CLK, HIGH);
  delayMicroseconds(100);
  digitalWrite(PIN_CLK, LOW);
}

void writeSPI(uint8_t data) {
  for (int i = 7; i >= 0; i--) {
    digitalWrite(PIN_DIN, (data & (1 << i)) ? HIGH : LOW);
    clk();
  }
}

unsigned long readSPI(uint8_t size_bits) {
  unsigned long value = 0;
  for (int i = size_bits - 1; i >= 0; i--) {
    if (digitalRead(PIN_DOUT)) {
      value |= (1 << i);
    }
    clk();
  }
  return value;
}

void chipSelect(uint8_t pin) {
  for (uint8_t i = 0; i < 4; i++) {
    if (cs_pins[i] != pin) {
      digitalWrite(cs_pins[i], HIGH);
    }
  }
  digitalWrite(pin, LOW);
}


/* ----------------------------------------------------- 
  ADC AD77x8 Functions
----------------------------------------------------- */
unsigned long read_register(unsigned char addr, unsigned int size_bits) {
  writeSPI(0x40 | addr); // WENB R/WB CR5 CR6 = 0x4
  digitalWrite(PIN_DIN, HIGH);
  unsigned long value = readSPI(size_bits);

  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();
  delay(10);
  return value;
}

void write_register(unsigned char addr, unsigned long value, unsigned int size_bits) {
  writeSPI(0x00 | addr); // WENB R/WB CR5 CR6 = 0x0

  for (int i = size_bits - 8; i >= 0; i -= 8) {
    writeSPI((value >> i) & 0xFF);
  }
  
  delay(10);
}

void rst() {
  digitalWrite(PIN_RSTB, LOW);
  delayMicroseconds(100);
  digitalWrite(PIN_RSTB, HIGH);
  
  // Setup IO control to set P1 and P2 to inputs
  // they are unconnected on the board and unused
  write_register(REG_IO_CONTROL, 0b00000000, 8);
}

void calibrate_channel(unsigned char channel_flag, String channel_name){
  Serial.println("Beginning calibration of channel " + channel_name);
  write_register(REG_MODE, 0b01100011, 8);
  //Serial.println("Mode set to " + String(read_register(REG_MODE,8), BIN));

  write_register(REG_ADC_CONTROL, channel_flag | ADC_CONTROL_RANGE_2p56V, 8);
  //Serial.println("Control set to " + String(read_register(REG_ADC_CONTROL,8), BIN));

  write_register(REG_MODE, MODE_ZERO_SCALE_CALIBRATION, 8);
  //Serial.println("Mode set to " + String(read_register(REG_MODE,8), BIN));

  //Serial.println("Before while loop");
  int cnt = 0;
  while(true) {
    unsigned long mode_value = read_register(REG_MODE, 8);
    //Serial.println("Mode A: " + String(mode_value, HEX));
    //Serial.println("Status: " + String(read_register(REG_STATUS, 8), BIN));
    if ((mode_value & 0x7) == MODE_IDLE) break;
    delay(10);
    cnt++;
    if (cnt > 100) {
      Serial.println("ERROR: Calibration failed, timeout.");
      return;
    }
  }

  Serial.println("Zero Scale Calibration succeeded!");

  write_register(REG_MODE, MODE_FULL_SCALE_CALIBRATION, 8);
  while(true) {
    unsigned long mode_value = read_register(REG_MODE, 8);
    // Serial.printf("Mode B: %02x\n", mode_value);
    if ((mode_value & 0x7) == MODE_IDLE) break;
    delay(10);
  }

  Serial.println("Calibration succeeded!");
}

unsigned long read_channel(unsigned char channel_id) {
  // write_register(REG_MODE, MODE_NEGBUF | MODE_REFSEL | MODE_CONTINUOUS_CONVERSION, 8); <- REFSEL results in bad range, ie results are clamped.
  write_register(REG_MODE, MODE_NEGBUF | MODE_CONTINUOUS_CONVERSION, 8);
  // unsigned long mode_value = read_register(REG_MODE, 8);
  // Serial.printf("mode:  %08x\n", mode_value);
  write_register(REG_ADC_CONTROL, ((channel_id - 1)<<4) | ADC_CONTROL_RANGE_2p56V, 8);
  // unsigned long control_value = read_register(REG_ADC_CONTROL, 8);
  // Serial.printf("control:  %08x\n", control_value);


  unsigned long try_count = 0;
  while (digitalRead(PIN_RDYB)) {
    delay(10);
    try_count++;
    if (try_count > 1000) {
      Serial.println("ERROR: Unable to read ADC value, timeout.");
      return 0;
    }
  }
  // unsigned long status = read_register(REG_STATUS, 8);
  // Serial.printf("status:  %08x\n", status);
  unsigned long adc_value = read_register(REG_ADC_DATA, ADC_BITS_AD7718);
  return adc_value;
}

void rw_register(Command cmd, bool enable, String name, unsigned char addr, unsigned int size_bits) {
  chipSelect(PIN_CSB);
  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();
  if (enable && (cmd.nargs > 0)) write_register(addr, hex2char(cmd.args[0]), size_bits);
  unsigned long value = read_register(addr, size_bits);
  Serial.println(name + " " + String(value, HEX));
  Serial.println();
}

/* ----------------------------------------------------- 
  Command Functions
----------------------------------------------------- */
void reset(Command cmd) {
  chipSelect(PIN_CSB);
  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();
  rst();
  delay(10);
  Serial.println(F("RESET COMPLETE\n"));
}

void calibrate(Command cmd) {
  chipSelect(PIN_CSB);
  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();

  if (cmd.nargs == 0){
    cmd.nargs = 8;
    cmd.args[0] = "1";
    cmd.args[1] = "2";
    cmd.args[2] = "3";
    cmd.args[3] = "4";
    cmd.args[4] = "5";
    cmd.args[5] = "6";
    cmd.args[6] = "7";
    cmd.args[7] = "8";
  } 

  for (uint8_t j=0; j<cmd.nargs; j++){
    byte channel_id = cmd.args[j].toInt();

    // skip iteration if invalid channel
    if (channel_id < 1 || channel_id > 8) {
        Serial.println(F("ERROR: Channel ID Invalid"));
        continue;
    }

    calibrate_channel((unsigned char)(channel_id-1), cmd.args[j]);
    delay(10);
  }
  Serial.println(F("CALIBRATION COMPLETE\n"));
}

void measure(Command cmd) {
  chipSelect(PIN_CSB);
  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();

  if (cmd.nargs == 0){
    Serial.println(F("ERROR: No channel selected for measurement\n"));
    return;
  }

  for (uint8_t j=0; j<cmd.nargs; j++){
    byte channel_id = cmd.args[j].toInt();

    // skip iteration if invalid channel
    if (channel_id < 1 || channel_id > 8) {
        Serial.println(F("ERROR: Channel ID Invalid"));
        continue;
    }

    unsigned long adc_value = read_channel(channel_id);
    Serial.println("measure " + String(channel_id) + " " + String(adc_value, HEX));
  }
  Serial.println(F("MEASUREMENT COMPLETE\n"));
}

void status(Command cmd){
  rw_register(cmd, false, "status", REG_STATUS, 8);
}

void mode(Command cmd) {
  rw_register(cmd, true, "mode", REG_MODE, 8);
}

void control(Command cmd) {
  rw_register(cmd, true, "control", REG_ADC_CONTROL, 8);
}

void io_control(Command cmd) {
  rw_register(cmd, true, "io_control", REG_IO_CONTROL, 8);
}

void gain(Command cmd) {
  rw_register(cmd, false, "gain", REG_ADC_GAIN, 24);
}

void offset(Command cmd) {
  rw_register(cmd, false, "offset", REG_ADC_OFFSET, 24);
}

void filter(Command cmd) {
  rw_register(cmd, true, "filter", REG_FILTER, 8);
}

void id(Command cmd) {
  rw_register(cmd, true, "id", REG_ID, 8);
}

void temp_probe(Command cmd) {
  if (cmd.nargs == 0){
    Serial.println(F("ERROR: No probe selected for measurement\n"));
    return;
  }

  for (uint8_t j=0; j<cmd.nargs; j++){
    byte probe_id = cmd.args[j].toInt();
    
    // skip iteration if invalid probe
    if (probe_id < 1 || probe_id > 3) {
        Serial.println(F("ERROR: Probe Invalid"));
        continue;
    }

    int cs_signal;
    //Serial.println("Before switch statement");
    switch (probe_id) {
      case 1:
        cs_signal = PIN_PROBE_1_CSB;
        break;
      case 2:
        cs_signal = PIN_PROBE_2_CSB;
        break;
      case 3:
        cs_signal = PIN_PROBE_3_CSB;
        break;
      default:
        Serial.println("ERROR: Invalid Probe ID");
        return;
    }
    delay(320);
    chipSelect(cs_signal);
    delay(10);
    unsigned long rawValue = readSPI(16);
    digitalWrite(cs_signal, HIGH);
    Serial.print("Probe " + String(probe_id) + ": 0x" + String(rawValue, HEX));
    
    rawValue >>= 3;

    // Handle negative temperatures (12-bit two's complement format)
    if (rawValue & 0x1000) {
      rawValue |= 0xE000;  // Sign extend to 16 bits if the temperature is negative
    }
    float temperatureC = rawValue * 0.0625;
  
    Serial.println("  " + String(temperatureC) + " °C");
    delay(1000);
  }
  Serial.println(F("TEMPERATURE READOUT COMPLETE\n"));
}


/* ----------------------------------------------------- 
  Setup 
----------------------------------------------------- */
CommandEntry command_table[] = {
  {"reset", reset},
  {"calibrate", calibrate},
  {"measure", measure},
  {"status", status},
  {"mode", mode},
  {"control", control},
  {"iocontrol", io_control},
  {"gain", gain},
  {"offset", offset},
  {"filter", filter},
  {"id", id},
  {"probe", temp_probe},
  {NULL, NULL}
};

void setup() {
  // put your setup code here, to run once:
  pinMode(PIN_CLK, OUTPUT);
  pinMode(PIN_DIN, OUTPUT);
  pinMode(PIN_CSB, OUTPUT);
  pinMode(PIN_PROBE_1_CSB, OUTPUT);
  pinMode(PIN_PROBE_2_CSB, OUTPUT); 
  pinMode(PIN_PROBE_3_CSB, OUTPUT);
  pinMode(PIN_RSTB, OUTPUT);

  digitalWrite(PIN_CLK, LOW);

  digitalWrite(PIN_DIN, HIGH);

  digitalWrite(PIN_CSB, LOW);
  digitalWrite(PIN_PROBE_1_CSB, HIGH);
  digitalWrite(PIN_PROBE_2_CSB, HIGH);
  digitalWrite(PIN_PROBE_3_CSB, HIGH);

  digitalWrite(PIN_RSTB, LOW);

  pinMode(PIN_DOUT, INPUT_PULLUP);
  pinMode(PIN_RDYB, INPUT_PULLDOWN);

  Serial.begin(9600);
}

void loop() {
  if (Serial.available() == 0) return;

  String line = Serial.readStringUntil('\n');

  Serial.println("Received command: " + line);
  Command command = parse_command(line);
  
  bool found = false;
  for (int i = 0; command_table[i].name != NULL; i++) {
    if (command.cmd == command_table[i].name) {
      command_table[i].func(command);
      found = true;
      break;
    }
  }
  if (!found) { 
    Serial.println("ERROR: Unknown command\n");
    return;
  }
}