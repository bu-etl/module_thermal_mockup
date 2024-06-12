#define MAX_ARGS 10

struct Command{
  String cmd;
  unsigned int nargs;
  String args[MAX_ARGS];
};

typedef void (*CommandFunc)(Command);

struct CommandEntry {
  const char* name;
  CommandFunc func;
};