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


class GithubRepositoryError(Exception):
    """
    Handles error codes from the Github API
    Parameters
    ----------
    error_code: Error code
    """
    def __init__(self, error_code):
        if error_code == 401:
            msg = f"The user is not authorized to access this resource or resource not found (Error code: {error_code})."
        # maybe not a good idea to trigger this in a test, as it could block user for a while
        # Docs on the error codes here:
        # https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api?apiVersion=2022-11-28#rate-limit-errors
        elif error_code in (403, 429):
            msg = f"Access forbidden due to exceeding rate limit (Error code: {error_code})"
        elif error_code == 404:
            msg = f"The requested resource does not exist (Error code: {error_code})"
        else:
            msg = f"Unknown error code: {error_code}"
        super(GithubRepositoryError, self).__init__(msg)
        self.error_code = error_code