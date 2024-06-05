#include <Arduino.h>
#include "command.h"

// Pin Assignments
#define PIN_DOUT 0
#define PIN_DIN 1
#define PIN_CLK 2
#define PIN_CS_B 3
#define PIN_RST_B 4
#define PIN_ENABLE_B 6
#define PIN_SEL_0 8
#define PIN_SEL_1 9
#define PIN_SEL_2 10
#define PIN_SEL_3 11
#define PIN_HEATER_3 12
#define PIN_HEATER_4 13
#define PIN_HEATER_2 18
#define PIN_HEATER_1 19

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

// TM Chip Select Addresses
#define TM_1_ADC 0x0
#define TM_1_PROBE_1 0x1
#define TM_1_PROBE_2 0x2
#define TM_1_PROBE_3 0x3
#define TM_2_ADC 0x4
#define TM_2_PROBE_1 0x5
#define TM_2_PROBE_2 0x6
#define TM_2_PROBE_3 0x7
#define TM_3_ADC 0x8
#define TM_3_PROBE_1 0x9
#define TM_3_PROBE_2 0xA
#define TM_3_PROBE_3 0xB
#define TM_4_ADC 0xC
#define TM_4_PROBE_1 0xD
#define TM_4_PROBE_2 0xE
#define TM_4_PROBE_3 0xF

/* ----------------------------------------------------- 
  Parsing Functions
----------------------------------------------------- */
unsigned char hex2char(String s) {
  if (s.length() < 2) {
    Serial.println("ERROR: Bad Hex conversion, must be two characters.");
    return 0;
  }
  unsigned char out = 0;
  for (uint8_t i=0; i<2; i++) {
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

// Ex: "command arg1 arg2 arg3" -> Command{cmd="command", nargs=3, args=["arg1", "arg2", "arg3"]}
Command parse_command(String line) {
  Command command;
  command.nargs = 0;
  int split;
  line.trim();

  // Parse the command
  split = line.indexOf(' ');
  if (split < 0) split = line.length();
  command.cmd = line.substring(0, split);
  line = line.substring(split);
  line.trim();

  // Parse the flag
  if (line.length() > 0 && line.charAt(0) == '-') {
    split = line.indexOf(' ');
    if (split < 0) split = line.length();
    command.flag = line.substring(1, split);
    line = line.substring(split);
    line.trim();
  } else {
    command.flag = "";
  }

  // Parse the arguments
  while(line.length() > 0 && command.nargs < MAX_ARGS) {
    split = line.indexOf(' ');
    if (split < 0) split = line.length();
    command.args[command.nargs] = line.substring(1, split);
    command.args[command.nargs].trim();
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

void chip_select(unsigned int addr) {
  digitalWrite(PIN_SEL_0, 0x1 & addr);
  digitalWrite(PIN_SEL_1, 0x1 & (addr>>1));
  digitalWrite(PIN_SEL_2, 0x1 & (addr>>2));
  digitalWrite(PIN_SEL_3, 0x1 & (addr>>3));
}

/* ----------------------------------------------------- 
  ADC AD77x8 Functions
----------------------------------------------------- */
void write_register(unsigned char addr, unsigned long value, unsigned int size_bits) {
  
  digitalWrite(PIN_DIN, LOW);  // WENB
  clk();
  digitalWrite(PIN_DIN, LOW);  // R/WB
  clk();
  digitalWrite(PIN_DIN, LOW); // CR5
  clk();
  digitalWrite(PIN_DIN, LOW); // CR6
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>3));  // ADDR bit 3
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>2));  // ADDR bit 2
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>1));  // ADDR bit 1
  clk();
  digitalWrite(PIN_DIN, 0x1 & addr);  // ADDR bit 0
  clk();

  unsigned long mask = 0x1 << (size_bits-1);
  for(uint8_t i=0; i<size_bits; i++) {
    if (mask & value) {
      digitalWrite(PIN_DIN, HIGH);
    } else {
      digitalWrite(PIN_DIN, LOW);
    }
    mask = mask >> 1;
    clk();
  }
  delay(10);
}

unsigned long read_register(unsigned char addr, unsigned int size_bits) {
  
  digitalWrite(PIN_DIN, LOW);  // WENB
  clk();
  digitalWrite(PIN_DIN, HIGH);  // R/WB
  clk();
  digitalWrite(PIN_DIN, LOW); // CR5
  clk();
  digitalWrite(PIN_DIN, LOW); // CR6
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>3));  // ADDR bit 3
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>2));  // ADDR bit 2
  clk();
  digitalWrite(PIN_DIN, 0x1 & (addr>>1));  // ADDR bit 1
  clk();
  digitalWrite(PIN_DIN, 0x1 & addr);  // ADDR bit 0
  clk();
  digitalWrite(PIN_DIN, HIGH);
  unsigned long value = 0;
  for(uint8_t i=0; i<size_bits; i++) {
    unsigned char bit = digitalRead(PIN_DOUT);
    value = value << 1;
    value = value | bit;
    clk();
  }
  clk(); clk(); clk(); clk();
  clk(); clk(); clk(); clk();
  delay(10);
  return value;
}

void rst() {
  digitalWrite(PIN_RST_B, LOW);
  delayMicroseconds(100);
  digitalWrite(PIN_RST_B, HIGH);
  
  // Setup IO control to set P1 and P2 to inputs
  // they are unconnected on the board and unused
  write_register(REG_IO_CONTROL, 0b00000000, 8);
}

void calibrate_channel(unsigned char channel_flag, String channel_name){
  Serial.println("Beginning calibration of channel " + channel_name);
  // write_register(REG_MODE, 0b01100011, 8);

  write_register(REG_ADC_CONTROL, channel_flag | ADC_CONTROL_RANGE_2p56V, 8);

  write_register(REG_MODE, MODE_ZERO_SCALE_CALIBRATION, 8);
  while(true) {
    unsigned long mode_value = read_register(REG_MODE, 8);
    // Serial.printf("Mode A: %02x\n", mode_value);
    if ((mode_value & 0x7) == MODE_IDLE) break;
    delay(10);
  }

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

  unsigned char adc_channel;
  if (channel_id >= 1 && channel_id <= 8) {
    adc_channel = channel_id - 1;  // Channels 1-8 map directly to 0x0-0x7
  } else if (channel_id == 9) {
    adc_channel = 0xE;  // AIN9 (as REFIN2+/AIN9)
  } else {
    Serial.println("ERROR: Unable to read ADC value, invalid channel ID.");
    return 0;
  }
  write_register(REG_ADC_CONTROL, (adc_channel << 4) | ADC_CONTROL_RANGE_2p56V, 8);
  // unsigned long control_value = read_register(REG_ADC_CONTROL, 8);
  // Serial.printf("control:  %08x\n", control_value);


  unsigned long try_count = 0;
  while(true) {
    unsigned long status_value = read_register(REG_STATUS, 8);
    if (status_value & STATUS_RDY) break;
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


/* ----------------------------------------------------- 
  Command Functions
----------------------------------------------------- */
void reset(Command cmd) {
  if (cmd.flag == "") {
    // loop through and reset ALL TM ADCs if no flag was given 
    for (uint8_t i=0; i<4; i++) {
      chip_select(i<<2);
      rst();
    }
    return;
  }

  // reset specific TM ADCs based on flag
  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    char board = cmd.flag.charAt(i);
    switch (board)
    {
    case 'a':
      chip_select(TM_1_ADC); rst(); break;
    case 'b':
      chip_select(TM_2_ADC); rst(); break;
    case 'c':
      chip_select(TM_3_ADC); rst(); break;
    case 'd': 
      chip_select(TM_4_ADC); rst(); break;
    default:
      Serial.println("ERROR: Invalid board selected for reset command.");
      break;
    }
  }
}

void calibrate(Command cmd) {
  Serial.print("Calibrating...");
}

void measure(Command cmd) {
  Serial.println("Measuring...");
}

void status(Command cmd) {
  Serial.println("Status...");
}

void unknown_command(Command cmd) {
  Serial.println("ERROR: Unknown command");
}


/* ----------------------------------------------------- 
  Setup 
----------------------------------------------------- */
CommandEntry command_table[] = {
  {"reset", reset},
  {"calibrate", calibrate},
  {"measure", measure},
  {"status", status},
  {NULL, unknown_command}
};

void setup() {
  pinMode(PIN_DOUT, INPUT_PULLUP);

  pinMode(PIN_CLK, OUTPUT);
  pinMode(PIN_DIN, OUTPUT);
  pinMode(PIN_CS_B, OUTPUT);
  pinMode(PIN_RST_B, OUTPUT);
  pinMode(PIN_ENABLE_B, OUTPUT);
  pinMode(PIN_SEL_0, OUTPUT);
  pinMode(PIN_SEL_1, OUTPUT);
  pinMode(PIN_SEL_2, OUTPUT);
  pinMode(PIN_SEL_3, OUTPUT);
  pinMode(PIN_HEATER_1, OUTPUT);
  pinMode(PIN_HEATER_2, OUTPUT);
  pinMode(PIN_HEATER_3, OUTPUT);
  pinMode(PIN_HEATER_4, OUTPUT);

  digitalWrite(PIN_CLK, LOW);
  digitalWrite(PIN_DIN, HIGH);
  digitalWrite(PIN_CS_B, HIGH);
  digitalWrite(PIN_RST_B, LOW);
  digitalWrite(PIN_ENABLE_B, LOW);
  digitalWrite(PIN_SEL_0, LOW);
  digitalWrite(PIN_SEL_1, LOW);
  digitalWrite(PIN_SEL_2, LOW);
  digitalWrite(PIN_SEL_3, LOW);
  digitalWrite(PIN_HEATER_1, LOW);
  digitalWrite(PIN_HEATER_2, LOW);
  digitalWrite(PIN_HEATER_3, LOW);
  digitalWrite(PIN_HEATER_4, LOW);

  Serial.begin(9600);
}

/* ----------------------------------------------------- 
  Main Logic Loop 
----------------------------------------------------- */
void loop() {
  if (Serial.available() == 0) return;

  String line = Serial.readStringUntil('\n');

  Command command = parse_command(line);
  
  bool found = false;
  for (int i = 0; command_table[i].name != NULL; i++) {
    if (command.cmd == command_table[i].name) {
      command_table[i].func(command);
      found = true;
      break;
    }
  }
  if (!found) unknown_command(command);
}
