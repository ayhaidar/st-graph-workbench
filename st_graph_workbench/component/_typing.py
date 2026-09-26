from typing import Any, Set, get_args


def literal_choices(literal_alias: Any) -> Set[str]:
    """Return string values declared by a `typing.Literal` alias."""
    return {str(choice) for choice in get_args(literal_alias)}
