"""Failure taxonomy so the caller can decide: retry when the outcome is
UNKNOWN (timeout / cut connection / 5xx), never retry when the server
ANSWERED (404 missing, 403 refused, other 4xx). Names carry the policy."""


class RetryableFetchError(RuntimeError):
    pass


class TerminalFetchError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
