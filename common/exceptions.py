class UIAgentError(Exception):
    pass


class AdapterError(UIAgentError):
    pass


class AIError(UIAgentError):
    pass


class CacheError(UIAgentError):
    pass


class ExecutorError(UIAgentError):
    pass
