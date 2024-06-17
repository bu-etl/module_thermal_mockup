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

// ADS1118 Config Register Settings
#define ADS1118_CONFIG_OS_SINGLE 0x8000    // Start single-conversion
#define ADS1118_CONFIG_MUX_AIN0  0x4000    // Mux AIN0
#define ADS1118_CONFIG_MUX_AIN1  0x5000    // Mux AIN1
#define ADS1118_CONFIG_MUX_AIN2  0x6000    // Mux AIN2
#define ADS1118_CONFIG_MUX_AIN3  0x7000    // Mux AIN3
#define ADS1118_CONFIG_PGA_6_144 0x0000    // ±6.144V range = Gain 2/3
#define ADS1118_CONFIG_MODE_SINGLE 0x0100  // Single-shot mode
#define ADS1118_CONFIG_DR_128SPS 0x0080    // 128 samples per second
#define ADS1118_CONFIG_TS_MODE 0x0004      // Temperature sensor mode
#define ADS1118_CONFIG_PULLUP 0x0002       // Enable pull-up
#define ADS1118_CONFIG_NOP 0x0001          // No operation

// TM Chip Select Addresses
#define TM_1_ADC 0x0
#define TM_2_ADC 0x4
#define TM_3_ADC 0x8
#define TM_4_ADC 0xC

const String allTM = "abcd";

/* ----------------------------------------------------- 
  Parsing Functions
----------------------------------------------------- */
unsigned char hex2char(String s) {
  if (s.length() < 2) {
    Serial.println(F("ERROR: Bad Hex conversion, must be two characters."));
    return 0;
  }
  unsigned char out = 0;
  for (uint8_t i=0; i<2; i++) {
    out = out << 4;
    char current = s.charAt(i);
    switch (toupper(current)) {
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
    command.args[command.nargs] = line.substring(0, split);
    command.args[command.nargs].trim();
    //Serial.println("Argument "+String(command.nargs) + ": " + command.args[command.nargs].c_str());
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

void chip_select(byte addr) {
  digitalWrite(PIN_SEL_0, 0x1 & addr);
  digitalWrite(PIN_SEL_1, 0x1 & (addr>>1));
  digitalWrite(PIN_SEL_2, 0x1 & (addr>>2));
  digitalWrite(PIN_SEL_3, 0x1 & (addr>>3));
  clk();
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


/* ----------------------------------------------------- 
  ADC AD77x8 Functions
----------------------------------------------------- */
void write_register(unsigned char addr, unsigned long value, byte size_bits) {

  writeSPI(0x00 | addr); // WENB R/WB CR5 CR6 = 0x0

  for (int i = size_bits - 8; i >= 0; i -= 8) {
    writeSPI((value >> i) & 0xFF);
  }
  delay(10);
}

unsigned long read_register(unsigned char addr, byte size_bits) {
  writeSPI(0x40 | addr); // WENB R/WB CR5 CR6 = 0x4
  digitalWrite(PIN_DIN, HIGH);
  unsigned long value = readSPI(size_bits);

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

  Serial.println(F("Calibration succeeded!"));
}

unsigned long read_channel(unsigned char channel_id) {
  // write_register(REG_MODE, MODE_NEGBUF | MODE_REFSEL | MODE_CONTINUOUS_CONVERSION, 8); <- REFSEL results in bad range, ie results are clamped.
  write_register(REG_MODE, MODE_NEGBUF | MODE_CONTINUOUS_CONVERSION, 8);

  write_register(REG_ADC_CONTROL, ((channel_id - 1)<<4) | ADC_CONTROL_RANGE_2p56V, 8);
  // unsigned long control_value = read_register(REG_ADC_CONTROL, 8);
  // Serial.printf("control:  %08x\n", control_value);


  unsigned long try_count = 0;
  while(true) {
    unsigned long status_value = read_register(REG_STATUS, 8);
    if (status_value & STATUS_RDY) break;
    try_count++;
    if (try_count > 1000) {
      Serial.println(F("ERROR: Unable to read ADC value, timeout."));
      return 0;
   }
  }

  // unsigned long status = read_register(REG_STATUS, 8);
  // Serial.printf("status:  %08x\n", status);
  unsigned long adc_value = read_register(REG_ADC_DATA, ADC_BITS_AD7718);
  return adc_value;
}


/* ----------------------------------------------------- 
  ADC ADS1118 Functions
----------------------------------------------------- */
unsigned long  readADS1118(uint16_t config) {
  
  digitalWrite(PIN_ENABLE_B, HIGH);
  digitalWrite(PIN_CS_B, LOW);

  writeSPI(config >> 8);
  writeSPI(config & 0xFF);

  digitalWrite(PIN_CS_B, HIGH);
  delay(10);  
  digitalWrite(PIN_CS_B, LOW);

  unsigned long result = readSPI(16);

  digitalWrite(PIN_CS_B, HIGH);
  digitalWrite(PIN_ENABLE_B, LOW);

  return result;
}


/* ----------------------------------------------------- 
  Multi-Board Helper Functions
----------------------------------------------------- */
int board_select(char board) {
  switch (board){
    case 'a':
      chip_select(TM_1_ADC); break;
    case 'b':
      chip_select(TM_2_ADC); break;
    case 'c':
      chip_select(TM_3_ADC); break;
    case 'd': 
      chip_select(TM_4_ADC); break;
    default:
      Serial.println(F("ERROR: Invalid board selected"));
      return -1;
      break;
  }
  return 0;
}

int probe_select(byte i) {
  switch (i){
    case 1:
      digitalWrite(PIN_SEL_0, HIGH);
      digitalWrite(PIN_SEL_1, LOW);
      break;
    case 2:
      digitalWrite(PIN_SEL_0, LOW);
      digitalWrite(PIN_SEL_1, HIGH);
      break;
    case 3:
      digitalWrite(PIN_SEL_0, HIGH);
      digitalWrite(PIN_SEL_1, HIGH);
      break;
    default:
      Serial.println(F("ERROR: Invalid probe selected"));
      return -1;
      break;
  }
  delayMicroseconds(10);
  return 0;
}

char cs2TM(byte i) {
  switch (i) {
    case 0x0 ... 0x3: return 'a';
    case 0x4 ... 0x7: return 'b';
    case 0x8 ... 0xB: return 'c';
    case 0xC ... 0xF: return 'd';
    default: return -1;
  }
}

void multi_read(String flag, String name, unsigned char addr, byte size){
  if (flag == "") {
    for (uint8_t i=0; i<4; i++) {
      chip_select(i<<2);
      unsigned long value = read_register(addr, size);
      Serial.println("TM Board " + String(cs2TM(i<<2)) + " " + name + ": 0x" + String(value, HEX));
    }
    return;
  }

  for (uint8_t i=0; i<flag.length(); i++) {
    char board = flag.charAt(i);
    Serial.println("Reading TM Board " + String(board));
    // skip itteration if invalid board
    if (board_select(board) == -1) continue;
    unsigned long value = read_register(addr, size);
    Serial.println("TM Board " + String(board) + " " + name + ": 0x" + String(value, HEX));
  }
}

void multi_write(String flag, String name, unsigned char addr, unsigned long value, byte size){
  if (flag == "") {
    for (uint8_t i=0; i<4; i++) {
      chip_select(i<<2);
      write_register(addr, value, size);
    }
    return;
  }

  for (uint8_t i=0; i<flag.length(); i++) {
    char board = flag.charAt(i);
    // skip itteration if invalid board
    if (board_select(board) == -1) continue;
    write_register(addr, value, size);
  }
}

Command removeArg(Command cmd) {
  //Serial.println("arg num: " + String(cmd.nargs));
  for (uint8_t i = 1; i < cmd.nargs; i++) {
    cmd.args[i-1] = cmd.args[i];
  }
  cmd.args[cmd.nargs - 1] = "";
  cmd.nargs--;
  return cmd;
}


/* ----------------------------------------------------- 
  Command Functions
----------------------------------------------------- */
void reset(Command cmd) {
  Serial.println(F("Resetting..."));

  digitalWrite(PIN_ENABLE_B, HIGH);
  delayMicroseconds(100);
  digitalWrite(PIN_ENABLE_B, LOW);

  if (cmd.flag == "") cmd.flag = allTM;

  // reset specific TM ADCs based on flag
  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    char board = cmd.flag.charAt(i);
    Serial.println("Resetting TM Board " + String(board));
    int status = board_select(board);
    if (status != -1) rst();
  }
  Serial.println(F("RESET COMPLETE\n"));
}

void calibrate(Command cmd) {
  Serial.println(F("Calibrating..."));
  
  if (cmd.flag == "") cmd.flag = allTM;

  // Calibrate specifc TM board(s)
  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    char board = cmd.flag.charAt(i);
    Serial.println("Calibrating TM Board " + String(board));

    // skip itteration if invalid board
    if (board_select(board) == -1) continue;

    if (cmd.nargs == 0) {
      // Calibrate all channels on the selected board
      for (uint8_t j=0; j<8; j++) {
        calibrate_channel((unsigned char)j, String(j+1));
      }
    } else {
      // Calibrate specific channel(s) on the selected board
      for (uint8_t j=0; j<cmd.nargs; j++) {
        byte channel_id = cmd.args[j].toInt();
        if (channel_id < 1 || channel_id > 8) {
          Serial.println(F("ERROR: Invalid channel selected for calibration command."));
          continue;
        }
        calibrate_channel((unsigned char)(channel_id-1), cmd.args[j]);
      }
    }
    Serial.println("\n");
  }
  Serial.println(F("CALIBRATION COMPLETE\n"));
}

void measure(Command cmd) {
  Serial.println(F("Measuring..."));
  if (cmd.nargs == 0) {
    Serial.println(F("ERROR: No channel selected for measurement."));
    return;
  }

  // Measure specified channels on all TM boards
  if (cmd.flag == ""){
    cmd.flag = allTM;
  }

  // Measure specified channels on specified TM boards
  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    //pick the TM board
    char board = cmd.flag.charAt(i);
    Serial.println("Measuring TM Board " + String(board));

    //skip itteration if invalid board
    if (board_select(board) == -1) continue;

    for (uint8_t j=0; j<cmd.nargs; j++) {
      //measure specified channels
      byte channel_id = cmd.args[j].toInt();

      //skip itteration if invalid channel
      if (channel_id < 1 || channel_id > 8) { 
        Serial.println(F("ERROR: Invalid channel selected to measure."));
        continue;
      }

      Serial.println("TM Board " + String(board) + " Channel " + cmd.args[j] + ": 0x" + String(read_channel(channel_id), HEX));
    }
    Serial.println("\n");
  }
  Serial.println(F("MEASURE COMPLETE\n"));
}

void status(Command cmd) {
  //Serial.println("Status...");
  multi_read(cmd.flag, "Status", REG_STATUS, 8);
  Serial.println("STATUS COMPLETE\n");
}

void offset(Command cmd) {
  //Serial.println("Offset...");
  multi_read(cmd.flag, "Offset", REG_ADC_OFFSET, 24);
  Serial.println(F("OFFSET COMPLETE\n"));
}

void gain(Command cmd) {
  //Serial.println("Gain...");
  multi_read(cmd.flag, "Gain", REG_ADC_GAIN, 24);
  Serial.println(F("GAIN COMPLETE\n"));
}

void mode(Command cmd){
  //Serial.println("Mode...");
  // Write mode register
  if (cmd.nargs > 0) multi_write(cmd.flag, "Mode", REG_MODE, hex2char(cmd.args[0]), 8);
  // Read mode register
  multi_read(cmd.flag, "Mode", REG_MODE, 8);
  Serial.println(F("MODE COMPLETE\n"));
}

void control(Command cmd){
  //Serial.println("Control...");
  // Write ADC Control register
  if (cmd.nargs > 0) multi_write(cmd.flag, "Control", REG_ADC_CONTROL, hex2char(cmd.args[0]), 8);
  // Read ADC Control register
  multi_read(cmd.flag, "Control", REG_ADC_CONTROL, 8);
  Serial.println(F("CONTROL COMPLETE\n"));
}

void io_control(Command cmd){
  //Serial.println("IO Control...");
  // Write IO Control register
  if (cmd.nargs > 0) multi_write(cmd.flag, "IO Control", REG_IO_CONTROL, hex2char(cmd.args[0]), 8);
  // Read IO Control register
  multi_read(cmd.flag, "IO Control", REG_IO_CONTROL, 8);
  Serial.println(F("IO CONTROL COMPLETE\n"));
}

void filter(Command cmd) {
  //Serial.println("Filter...");
  // Write Filter register
  if (cmd.nargs > 0) multi_write(cmd.flag, "Filter", REG_FILTER, hex2char(cmd.args[0]), 8);
  // Read Filter register
  multi_read(cmd.flag, "Filter", REG_FILTER, 8);
  Serial.println(F("FILTER COMPLETE\n"));
}

void id(Command cmd){
  //Serial.println("ID...");
  // Write ID register
  if (cmd.nargs > 0) multi_write(cmd.flag, "ID", REG_ID, hex2char(cmd.args[0]), 8);
  // Read ID register
  multi_read(cmd.flag, "ID", REG_ID, 8);
  Serial.println(F("ID COMPLETE\n"));
}

void temp_probe(Command cmd){
  //Serial.println("Temp Probe...");

  if (cmd.flag == "") cmd.flag = allTM;
  if (cmd.nargs == 0) {
    cmd.nargs = 3;
    cmd.args[0] = "1";
    cmd.args[1] = "2";
    cmd.args[2] = "3";
  }
  
  //Serial.println("flag: " + cmd.flag + " nargs: " + String(cmd.nargs));

  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    char board = cmd.flag.charAt(i);
    Serial.println("Reading TM Board " + String(board));

    // skip itteration if invalid board
    if (board_select(board) == -1) continue;

    for (uint8_t j=0; j<cmd.nargs; j++) {

      // skip itteration if invalid probe
      int probe = cmd.args[j].toInt();
      if (probe_select(probe) == -1) continue;
      unsigned long rawValue = readSPI(16);

      Serial.println("Temp Probe " + String(probe) + ": 0x" + String(rawValue, HEX));
    }
    Serial.println("\n");
  }
  board_select('a');
  delay(10);
  Serial.println(F("TEMP PROBE READ COMPLETE\n"));
}

void heater(Command cmd){
  //Serial.println("Heater...");
  if (cmd.nargs == 0) {
    Serial.println("ERROR: No heater state selected.");
    return;
  }

  String state = cmd.args[0];
  state.toUpperCase();
  if (state != "ON" && state != "OFF") {
    Serial.println("ERROR: Invalid heater state selected.");
    return;
  }

  if (cmd.flag == "") cmd.flag = allTM;

  byte control = (state == "ON") ? HIGH : LOW;

  for (uint8_t i=0; i<cmd.flag.length(); i++){
    char board = cmd.flag.charAt(i);
    
    // skip itteration if invalid board
    if (board_select(board) == -1) continue;

    switch (board){
      case 'a':
        digitalWrite(PIN_HEATER_1, control);
        break;
      case 'b':
        digitalWrite(PIN_HEATER_2, control);
        break;
      case 'c':
        digitalWrite(PIN_HEATER_3, control);
        break;
      case 'd':
        digitalWrite(PIN_HEATER_4, control);
        break;
      default:
        break;
    }
    Serial.println("Heater " + String(board) + " " + state);
  }
  Serial.println(F("HEATER TOGGLE COMPLETE\n"));
}

void current(Command cmd){
  if (cmd.nargs != 0){
    Serial.println(F("ERROR: Current command does not accept arguments."));
    return;
  }

  if (cmd.flag == "") cmd.flag = allTM;

  for (uint8_t i=0; i<cmd.flag.length(); i++) {
    char board = cmd.flag.charAt(i);
    //Serial.println("Current reading TM Board " + String(board));

    // skip itteration if invalid board
    if (board_select(board) == -1) continue;
    uint16_t config = ADS1118_CONFIG_OS_SINGLE | ADS1118_CONFIG_PGA_6_144 | ADS1118_CONFIG_MODE_SINGLE | ADS1118_CONFIG_DR_128SPS;

    uint16_t value = readADS1118(config);
    switch (board)
    {
    case 'a':
      config |= ADS1118_CONFIG_MUX_AIN0;
      break;
    case 'b':
      config |= ADS1118_CONFIG_MUX_AIN1;
      break;
    case 'c':
      config |= ADS1118_CONFIG_MUX_AIN2;
      break;
    case 'd':
      config |= ADS1118_CONFIG_MUX_AIN3;
      break;
    default:
      break;
    }

    value = readADS1118(config);
    Serial.println("TM board " + String(board) + " current Reading: 0x" + String(value, HEX));
  }

  Serial.println(F("CURRENT READING COMPLETE\n"));
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
  {"heater", heater},
  {"current", current},
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
  digitalWrite(PIN_ENABLE_B, HIGH);
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
  if (!found) Serial.println("ERROR: Unknown command");
}

