# Copy this file to rules_private.py and fill in your personal rules.
#
#   cp config/rules_private.example.py config/rules_private.py

# --- Name-matching rules ---
# Each entry: ([substrings], [tags])
# A transaction matches if ANY substring is found in the name (case-insensitive).
# The special tag "recurrent" prevents date-range rules from also tagging the transaction.
NAME_TAG_RULES: list[tuple[list[str], list[str]]] = [
    # Utilities & recurrent costs
    # (["Water Company", "Phone Provider"], ["utilities", "recurrent"]),
    # Groceries
    # (["Supermarket Name"], ["groceries"]),
    # Salary
    # (["Employer Name"], ["salary", "recurrent"]),
    # Add your own rules here...
]

# --- Date-range rules ---
# Each entry: (start, end, [tags])
# start/end accept either "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS".
# Date-only boundaries expand to 00:00:00 (start) and 23:59:59 (end).
# Applied only when the transaction does NOT already carry the "recurrent" tag.
DATE_RANGE_TAG_RULES: list[tuple[str, str, list[str]]] = [
    # ("2025-07-01", "2025-07-14", ["vacation", "trip to somewhere"]),
]
