INPUT_FOLDER = "data/input"
OUTPUT_FOLDER = "data/output"

try:
    from .rules_private import NAME_TAG_RULES, DATE_RANGE_TAG_RULES  # noqa: F401
except ImportError as e:
    raise ImportError(
        "config/rules_private.py not found. "
        "Copy config/rules_private.example.py to config/rules_private.py and fill in your rules."
    ) from e
