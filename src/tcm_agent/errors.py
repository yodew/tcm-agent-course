"""Public errors never include upstream payloads or health information."""


class AgentError(Exception):
    """Expected failure with a stable public code."""

    def __init__(self, code: str, status: int = 503) -> None:
        super().__init__(code)
        self.code: str = code
        self.status: int = status


class DataContractError(ValueError):
    """Invalid administrator data or numeric contract, with a stable reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code: str = code


class ConfigurationError(ValueError):
    """Invalid settings; Pydantic reports the code with input values hidden."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code: str = code
