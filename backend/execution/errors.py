class ExecutionError(Exception):
    pass


class RateLimitError(ExecutionError):
    pass


class ExchangeRejectedOrder(ExecutionError):
    pass


class InsufficientFunds(ExecutionError):
    pass