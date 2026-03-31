"""Domain errors surfaced to the UI and CLI in a user-safe form."""


class StudyAgentError(Exception):
    """Configuration, validation, or wrapped upstream failures (OpenAI, PDF, etc.)."""
