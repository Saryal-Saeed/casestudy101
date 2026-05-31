"""
Tests for the People Ops workflows.

Nothing fancy here. Just plain assert-based tests I can run with `python -m src.test_workflows`.
I didn't pull in pytest since the instructions said "any framework or even a simple assert script".
"""

from datetime import date

from integrations.hris import HRISClient
from integrations.it_tasks import ITTasksClient
from src.date_utils import parse_date, working_days_before
from src.validator import validate_new_hire, validate_offboarding
from src.workflows import process_new_hire, process_offboarding


def test_working_days_before():
    # Feb 3, 2025 is a Monday so it is a good anchor for testing weekend skipping
    monday = date(2025, 2, 3)

    # 1 working day before Monday should land on Friday
    friday = working_days_before(monday, 1)
    assert friday == date(2025, 1, 31), f"Expected 2025-01-31, got {friday}"

    # 3 working days back from Monday = previous Wednesday
    wednesday = working_days_before(monday, 3)
    assert wednesday == date(2025, 1, 29), f"Expected 2025-01-29, got {wednesday}"

    # 0 days should give us the same date back
    same_day = working_days_before(monday, 0)
    assert same_day == monday, f"Expected {monday}, got {same_day}"


def test_validator_new_hire():
    # happy path where all fields present
    valid_event = {
        "event_id": "1",
        "type": "new_hire",
        "employee": {
            "first_name": "A",
            "last_name": "B",
            "email": "a@b.com",
            "team": "Eng",
            "start_date": "2025-01-01"
        }
    }
    assert len(validate_new_hire(valid_event)) == 0

    # missing event_id and employee entirely
    invalid_event = {
        "type": "new_hire",
    }
    errors = validate_new_hire(invalid_event)
    assert len(errors) > 0


def test_validator_offboarding():
    valid_event = {
        "event_id": "1",
        "type": "offboarding",
        "employee_email": "a@b.com",
        "last_day": "2025-01-01"
    }
    assert len(validate_offboarding(valid_event)) == 0


def test_process_new_hire_success():
    # spin up fresh clients so tests don't interfere with each other
    hris = HRISClient()
    it_tasks = ITTasksClient()

    event = {
        "event_id": "evt_test_1",
        "type": "new_hire",
        "employee": {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@company.com",
            "start_date": "2025-02-03",  # a Monday
            "team": "Engineering",
            "role": "Engineer",
            "manager": "manager@company.com",
            "location": "Berlin"
        }
    }

    result = process_new_hire(event, hris=hris, it_tasks=it_tasks)

    assert result["status"] == "completed"
    # 1 HRIS create + 3 standard tasks + 1 GitHub (Engineering team)
    assert len(result["actions_taken"]) == 5

    # verify employee actually landed in the mock HRIS
    assert "test.user@company.com" in hris._employees

    # 4 IT tasks total (3 standard + GitHub)
    tasks = list(it_tasks._tasks.values())
    assert len(tasks) == 4


def test_process_new_hire_idempotency():
    """Run the same event twice. Should NOT create duplicate tasks."""
    hris = HRISClient()
    it_tasks = ITTasksClient()

    event = {
        "event_id": "evt_test_2",
        "type": "new_hire",
        "employee": {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user2@company.com",
            "start_date": "2025-02-03",
            "team": "Sales",
            "role": "AE",
            "manager": "manager@company.com",
            "location": "Berlin"
        }
    }

    # first run
    result1 = process_new_hire(event, hris=hris, it_tasks=it_tasks)
    assert result1["status"] == "completed"

    tasks_count_1 = len(it_tasks._tasks)
    assert tasks_count_1 == 3  # 3 standard tasks (Sales, no GitHub)

    # second run with the exact same event
    result2 = process_new_hire(event, hris=hris, it_tasks=it_tasks)
    assert result2["status"] == "completed"

    # should STILL be 3 because idempotency keys prevent duplicates
    tasks_count_2 = len(it_tasks._tasks)
    assert tasks_count_2 == 3, "Duplicate tasks were created despite idempotency keys"


def test_process_offboarding_success():
    hris = HRISClient()
    it_tasks = ITTasksClient()

    # manually add the employee so the lookup works
    hris._employees["leaving@company.com"] = {
        "id": "123",
        "first_name": "Leave",
        "last_name": "Person",
        "email": "leaving@company.com",
        "team": "Design"
    }

    event = {
        "event_id": "evt_test_3",
        "type": "offboarding",
        "employee_email": "leaving@company.com",
        "last_day": "2025-02-03"  # Monday
    }

    result = process_offboarding(event, hris=hris, it_tasks=it_tasks)

    assert result["status"] == "completed"
    # 1 lookup + 1 update + 3 tasks = 5 actions
    assert len(result["actions_taken"]) == 5

    # check that end_date got set
    assert hris._employees["leaving@company.com"].get("end_date") == "2025-02-03"

    tasks = list(it_tasks._tasks.values())
    assert len(tasks) == 3

    # the "revoke all access" task should be due ON the last day (0 working days before)
    revoke_task = next(t for t in tasks if "Revoke email" in t.title)
    assert revoke_task.due_date == "2025-02-03"


if __name__ == "__main__":
    print("Running tests...")
    test_working_days_before()
    test_validator_new_hire()
    test_validator_offboarding()
    test_process_new_hire_success()
    test_process_new_hire_idempotency()
    test_process_offboarding_success()
    print("All tests passed!")
