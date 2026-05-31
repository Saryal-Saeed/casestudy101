"""
Input validation for People Ops events.

Checks that required fields are present before we try to process anything.
"""


def validate_new_hire(event: dict):
    """
    Check that a new_hire event has everything we need.
    Returns a list of error strings (empty = all good).
    """
    errors = []

    # top-level stuff
    for field in ["event_id", "type"]:
        if field not in event:
            errors.append(f"Missing required field: '{field}'")

    # make sure 'employee' exists and is actually a dict
    employee = event.get("employee")

    if not isinstance(employee, dict):
        errors.append("Missing or invalid 'employee' object")
        # can't check sub-fields if employee itself is missing
        return errors

    # required fields inside the employee object
    for field in ["first_name", "last_name", "email", "team", "start_date"]:
        if field not in employee:
            errors.append(f"Missing required employee field: '{field}'")

    return errors


def validate_offboarding(event: dict) -> list[str]:
    """
    Check that an offboarding event has everything we need.
    Returns a list of error strings (empty = all good).
    """
    errors = []

    # offboarding events are flat with no nested employee object
    for field in ["event_id", "type", "employee_email", "last_day"]:
        if field not in event:
            errors.append(f"Missing required field: '{field}'")

    return errors
