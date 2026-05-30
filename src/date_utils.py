"""
Date utility functions for People Ops Automation.

Handles working day calculations (Monday-Friday, no weekends).
"""

from datetime import datetime
from datetime import date, timedelta


def working_days_before(start_date: date, days: int) -> date:
    """
    Calculate a date that is N working days before start_date.

    Working days = Monday to Friday (weekends are skipped).

    Args:
        start_date: The reference date (e.g., employee's first day).
        days: How many working days to go back.

    Returns:
        A date object representing the calculated due date.
    """
    current = start_date
    counted = 0

    while counted < days:
        # Move back one day
        current = current - timedelta(days=1)

        # Check if this day is a weekday (Mon=0 ... Fri=4, Sat=5, Sun=6)
        if current.weekday() < 5:
            counted += 1

    return current


def parse_date(date_string: str) -> date:
    """
    Parse a date string like '2025-02-01' into a date object.

    Args:
        date_string: Date in 'YYYY-MM-DD' format.

    Returns:
        A date object.

    Raises:
        ValueError: If the string is not in the correct format.
    """
    return date.fromisoformat(date_string)
