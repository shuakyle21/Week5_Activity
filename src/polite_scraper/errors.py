"""Failure taxonomy so the caller can decide: retry when the outcome is
UNKNOWN (timeout / cut connection / 5xx), never retry when the server
ANSWERED (404 missing, 403 refused, other 4xx). Names carry the policy."""


class RetryableFetchError(RuntimeError):
    pass


class TerminalFetchError(RuntimeError):
    pass
