#define MAX_ARGS 10

struct Command{
  String cmd;
  unsigned int nargs;
  String args[MAX_ARGS];
};