"""
Validator module for People Ops Automation.

Validates incoming event data before processing workflows.
"""


def validate_new_hire(event: dict):
    """
    Validate a new_hire event has all required fields.

    Args:
        event: The raw event dictionary loaded from JSON.

    Returns:
        A list of error messages. Empty list means the input is valid.
    """
    errors = []

    # --- Step A: Check top-level required fields ---
    top_level_fields = ["event_id", "type"]

    for field in top_level_fields:
        if field not in event:
            errors.append(f"Missing required field: '{field}'")

    # --- Step B: Check that 'employee' key exists and is a dict ---
    employee = event.get("employee")

    if not isinstance(employee, dict):
        errors.append("Missing or invalid 'employee' object")
        # If employee is missing entirely, we can't check its sub-fields
        # so we return early with the errors we have so far
        return errors

    # --- Step C: Check required employee sub-fields ---
    employee_fields = ["first_name", "last_name", "email", "team", "start_date"]

    for field in employee_fields:
        if field not in employee:
            errors.append(f"Missing required employee field: '{field}'")

    return errors


def validate_offboarding(event: dict) -> list[str]:
    """
    Validate an offboarding event has all required fields.

    Args:
        event: The raw event dictionary loaded from JSON.

    Returns:
        A list of error messages. Empty list means the input is valid.
    """
    errors = []

    # Offboarding events have a flat structure (no nested 'employee' object).
    # Required fields: event_id, type, employee_email, last_day
    required_fields = ["event_id", "type", "employee_email", "last_day"]

    for field in required_fields:
        if field not in event:
            errors.append(f"Missing required field: '{field}'")

    return errors
