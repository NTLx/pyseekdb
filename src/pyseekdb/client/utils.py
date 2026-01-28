"""
General utility functions for pyseekdb client.
"""

from typing import Any


def unflatten_dict(flat_dict: dict[str, Any], delimiter: str = ".") -> dict[str, Any]:
    """
    Unflatten a dictionary with delimited keys into a nested structure.
    Example: {"metadata.user.id": 1} -> {"metadata": {"user": {"id": 1}}}

    Args:
        flat_dict: A dictionary where keys might contain the delimiter.
        delimiter: The character used to separate nested keys.

    Returns:
        A nested dictionary structure.
    """
    nested_dict: dict[str, Any] = {}
    for key, value in flat_dict.items():
        parts = key.split(delimiter)
        d = nested_dict
        for part in parts[:-1]:
            if part not in d or not isinstance(d[part], dict):
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return nested_dict
