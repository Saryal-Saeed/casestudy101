"""
Date helpers mostly for calculating "N working days before" a given date.
Working days = Mon-Fri, no holiday calendar (see README assumptions).
"""

from datetime import datetime
from datetime import date, timedelta


def working_days_before(start_date: date, days: int) -> date:
    """
    Go back N working days from start_date, skipping weekends.

    For example, 1 working day before a Monday gives you the previous Friday.
    If days=0, just returns start_date as-is.
    """
    current = start_date
    counted = 0

    while counted < days:
        current = current - timedelta(days=1)
        # weekday(): Mon=0, Tue=1, ... Fri=4, Sat=5, Sun=6
        if current.weekday() < 5:
            counted += 1

    return current


def parse_date(date_string: str) -> date:
    """Parse a 'YYYY-MM-DD' string into a date object."""
    return date.fromisoformat(date_string)
