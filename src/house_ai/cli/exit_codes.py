"""The exit codes every ``house-ai`` command returns."""

EXIT_OK = 0
#: The command ran and something failed: a check, a blocked gate, a wrong phrase.
EXIT_FAIL = 1
#: The command was refused or misused: no terminal, a non-human identity, bad arguments.
EXIT_USAGE = 2
