"""
Specific classes to handle errors.
"""


class BadRequestException(Exception):
    """Handle bad request exceptions and shows improved messages.

    Parameters
    ----------
    rv : requests.Response
        The request variable returned that caused the error.
    """
    def __init__(self, rv):
        msg = "Server returned status {}. Reason: {}".format(rv.status_code, rv.reason)
        super(BadRequestException, self).__init__(msg)
        self.rv = rv


class TimeOutException(Exception):
    """Handle TimeOut exceptions and shows improved messages.

    Parameters
    ----------
    rv : requests.Response
        The request variable returned that caused the error.
    """
    def __init__(self, rv):
        msg = ("Server exceeded the max time to process request. " +
               "Status: {}; Reason: {}".format(rv.status_code, rv.reason))
        super(TimeOutException, self).__init__(msg)
        self.rv = rv
