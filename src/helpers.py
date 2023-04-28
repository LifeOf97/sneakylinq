# from src.utils import redis_client


def is_valid_alias(alias: str) -> tuple[str, bool]:
    """Check the validity of an alias"""
    alias: str = alias.lower()

    status: bool = True
    message: str = "Alias saved successfully"

    if "." in str(alias):
        status = False
        message = "Alias cannot contain period (.) sign."

    if str(alias).isnumeric():
        status = False
        message = (
            "Alias must be a mix of letters & numbers, and can contain underscores"
        )

    if len(str(alias)) < 4 or len(str(alias)) > 15:
        status = False
        message = "Alias must be between 4 to 15 characters long"

    if alias in ["sneaky", "linq"]:
        status = False
        message = "Alias cannot be a reserved word"

    return (message, status)


def format_alias(alias: str) -> str:
    """Append the word (.linq) to a username"""
    return f"{alias.strip('.').lower()}.linq"
