"""Errors for colpeek.

One exception type, carrying a message a human can act on. The CLI turns
these into a one-line stderr message plus a non-zero exit code — no
tracebacks for the person just trying to look at their CSV.
"""


class ColpeekError(Exception):
    """Something went wrong with the input file or the request.

    `exit_code` is what the process should return: 1 for problems with the
    file itself (missing, empty, unreadable), 2 is reserved for argparse
    usage errors.
    """

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
