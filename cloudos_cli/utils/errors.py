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
        # Try to get the message from response body first
        error_message = None
        try:
            response_body = rv.json()
            error_message = response_body.get('message')
        except (ValueError, AttributeError):
            # Response is not JSON or doesn't have expected structure
            pass
        
        # Prioritize message from response, fallback to reason
        if error_message:
            msg = "Server returned status {}. Message: {}".format(rv.status_code, error_message)
        else:
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


class AccountNotLinkedException(Exception):
    """
    Displays a meaningful message when the user tries to import a repository from an account that is not linked
    with their cloudOS account
    """
    def __init__(self, wf_url):
        msg = (f"The pipeline at the URL {wf_url} cannot be imported. Check that you repository account " +
               "has been linked in your cloudOS workspace")
        super(AccountNotLinkedException, self).__init__(msg)
        self.wf_url = wf_url


class JoBNotCompletedException(Exception):
    def __init__(self, job, status):
        msg = f"Job {job} has status {status}. Results are only available for jobs with status \"completed\""
        super(JoBNotCompletedException, self).__init__(msg)
        self.job = job
        self.status = status


class NotAuthorisedException(Exception):
    def __init__(self):
        msg = ("Not authorised to run this operation. Check your API key, and that the resource you request is "
               "in the same workspace as the workspace specified in the cloudOS cli")
        super(NotAuthorisedException, self).__init__(msg)


class NoCloudForWorkspaceException(Exception):
    def __init__(self, workspace_id):
        msg = f"Workspace ID {workspace_id} is not associated with supported cloud providers. Check the workspace ID"
        super(NoCloudForWorkspaceException, self).__init__(msg)
        self.workspace_id = workspace_id
