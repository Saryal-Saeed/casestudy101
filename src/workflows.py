"""
Workflows for processing People Ops events (new hire + offboarding).

I kept each workflow as a standalone function instead of building a class
hierarchy, since each call is basically fire-and-forget. There is no state to
carry around between calls. Functions felt simpler.

The integration clients (HRIS, IT tasks) are optional params so I can
inject mocks during testing. Every external call is wrapped in try/except
so one flaky service can't take down the whole workflow.
"""

from datetime import datetime

from integrations.hris import HRISClient, HRISError
from integrations.it_tasks import ITTasksClient, ITTasksError
from src.validator import validate_new_hire, validate_offboarding
from src.date_utils import parse_date, working_days_before


# ---- New Hire Workflow ----

def process_new_hire(
    event: dict,
    hris: HRISClient | None = None,
    it_tasks: ITTasksClient | None = None,
) -> dict:
    """
    Process a new_hire event end-to-end.

    Validates input, creates the employee in HRIS, spins up onboarding
    tasks in the IT system, and returns a structured result dict.

    Args:
        event:    Raw event dict from the JSON input.
        hris:     Optional client to pass for testing.
        it_tasks: Optional client to pass for testing.

    Returns:
        Result dict matching the expected output format.
    """

    # Validate first, bail early if something's missing
    errors = validate_new_hire(event)
    if errors:
        return {
            "event_id": event.get("event_id", "unknown"),
            "event_type": "new_hire",
            "status": "error",
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "errors": errors,
            "actions_taken": [],
            "summary": f"Validation failed with {len(errors)} error(s).",
        }

    # Create clients if caller didn't provide them
    if hris is None:
        hris = HRISClient()
    if it_tasks is None:
        it_tasks = ITTasksClient()

    employee = event["employee"]
    start_date = parse_date(employee["start_date"])

    # We'll collect every action we take (successes AND failures) here
    actions_taken = []

    # -- Create employee record in HRIS --
    try:
        hris_result = hris.create_employee(employee)

        if hris_result.success:
            actions_taken.append({
                "integration": "hris",
                "action": "create_employee",
                "success": True,
                "details": f"Created employee record for {employee['email']}",
            })
        else:
            # HRIS said no (maybe employee already exists). This is not a crash, just log it
            actions_taken.append({
                "integration": "hris",
                "action": "create_employee",
                "success": False,
                "details": hris_result.error,
            })
    except HRISError as e:
        # actual service blew up (network issue, etc.)
        actions_taken.append({
            "integration": "hris",
            "action": "create_employee",
            "success": False,
            "details": str(e),
        })

    # -- Build the list of onboarding tasks --
    # I'm reading the equipment info from the event so the task description
    # reflects what was actually requested (e.g. "MacBook Pro 14" + monitor + headset")
    equipment = event.get("equipment", {})
    equipment_parts = []
    if equipment.get("laptop"):
        # laptop value can be a string like "MacBook Pro 14" or just True
        laptop_name = equipment["laptop"] if isinstance(equipment["laptop"], str) else "laptop"
        equipment_parts.append(laptop_name)
    if equipment.get("monitor"):
        equipment_parts.append("monitor")
    if equipment.get("headset"):
        equipment_parts.append("headset")
    equipment_desc = " + ".join(equipment_parts) if equipment_parts else "laptop + monitor + headset"

    onboarding_tasks = [
        {
            "title": "Create email and Slack accounts",
            "description": f"Set up email and Slack for {employee['first_name']} {employee['last_name']}",
            "assignee": "it-team@company.com",
            "due_days_before": 3,
            "task_key": "email_slack_setup",
        },
        {
            "title": f"Order {equipment_desc}",
            "description": f"Order equipment for {employee['first_name']} {employee['last_name']}",
            "assignee": "it-team@company.com",
            "due_days_before": 5,
            "task_key": "order_equipment",
        },
        {
            "title": "Schedule Day 1 orientation",
            "description": (
                f"Schedule orientation for {employee['first_name']} "
                f"{employee['last_name']} on {employee['start_date']}"
            ),
            "assignee": "people@company.com",
            "due_days_before": 1,
            "task_key": "day1_orientation",
        },
    ]

    # Engineering gets an extra GitHub access task
    if employee.get("team") == "Engineering":
        onboarding_tasks.append({
            "title": "Grant GitHub access",
            "description": (
                f"Add {employee['first_name']} {employee['last_name']} "
                f"to the Engineering GitHub organization"
            ),
            "assignee": "it-team@company.com",
            "due_days_before": 3,
            "task_key": "github_access",
        })

    # -- Create each task in the IT system --
    # For each one we check idempotency first (does a task with this key
    # already exist?) then calculate the due date and create it.
    task_count = 0

    for task_def in onboarding_tasks:
        try:
            # build a unique key so re-running the same event won't create duplicates
            idempotency_key = f"{event['event_id']}_{task_def['task_key']}"
            existing = it_tasks.find_task_by_metadata("idempotency_key", idempotency_key)

            if existing:
                # already done, skip but still count it
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": True,
                    "details": (
                        f"Task {existing.task_id}: {task_def['title']} "
                        f"(already exists, skipped)"
                    ),
                })
                task_count += 1
                continue

            due_date = working_days_before(start_date, task_def["due_days_before"])

            result = it_tasks.create_task(
                title=task_def["title"],
                description=task_def["description"],
                assignee=task_def["assignee"],
                due_date=str(due_date),
                metadata={
                    "event_id": event["event_id"],
                    "idempotency_key": idempotency_key,
                },
            )

            if result.success:
                task = result.task
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": True,
                    "details": (
                        f"Task {task.task_id}: {task_def['title']} "
                        f"(assigned to: {task_def['assignee']}, due: {due_date})"
                    ),
                })
                task_count += 1
            else:
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": False,
                    "details": result.error,
                })

        except ITTasksError as e:
            actions_taken.append({
                "integration": "it_tasks",
                "action": "create_task",
                "success": False,
                "details": str(e),
            })

    # -- Done, return the result --
    return {
        "event_id": event["event_id"],
        "event_type": "new_hire",
        "status": "completed",
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "actions_taken": actions_taken,
        "summary": (
            f"Onboarding initiated for {employee['first_name']} {employee['last_name']} "
            f"({employee['team']}, starting {employee['start_date']}). "
            f"Created employee record and {task_count} onboarding tasks."
        ),
    }


# ---- Offboarding Workflow ----

def process_offboarding(
    event: dict,
    hris: HRISClient | None = None,
    it_tasks: ITTasksClient | None = None,
) -> dict:
    """
    Process an offboarding event end-to-end.

    Looks up the employee, sets their end_date in HRIS, then creates
    offboarding tasks (equipment return, access revocation, etc.)
    with due dates relative to their last day.

    Args:
        event:    Raw event dict from JSON.
        hris:     Optional HRISClient for testing.
        it_tasks: Optional ITTasksClient for testing.

    Returns:
        Result dict in the same shape as the new hire workflow.
    """

    # validate
    errors = validate_offboarding(event)
    if errors:
        return {
            "event_id": event.get("event_id", "unknown"),
            "event_type": "offboarding",
            "status": "error",
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "errors": errors,
            "actions_taken": [],
            "summary": f"Validation failed with {len(errors)} error(s).",
        }

    if hris is None:
        hris = HRISClient()
    if it_tasks is None:
        it_tasks = ITTasksClient()

    employee_email = event["employee_email"]
    last_day = parse_date(event["last_day"])
    actions_taken = []

    # -- Look up the employee --
    # Instructions say to "fail clearly if they don't exist", so we return
    # an error result instead of continuing blindly.
    try:
        lookup = hris.get_employee(employee_email)

        if not lookup.success:
            return {
                "event_id": event["event_id"],
                "event_type": "offboarding",
                "status": "error",
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "errors": [lookup.error],
                "actions_taken": [],
                "summary": f"Employee not found: {employee_email}",
            }

        employee_data = lookup.data
        actions_taken.append({
            "integration": "hris",
            "action": "get_employee",
            "success": True,
            "details": f"Found employee record for {employee_email}",
        })

    except HRISError as e:
        return {
            "event_id": event["event_id"],
            "event_type": "offboarding",
            "status": "error",
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "errors": [str(e)],
            "actions_taken": [],
            "summary": f"Failed to look up employee: {e}",
        }

    # -- Update HRIS with end_date --
    try:
        update_result = hris.update_employee(
            employee_email, {"end_date": str(last_day)}
        )

        if update_result.success:
            actions_taken.append({
                "integration": "hris",
                "action": "update_employee",
                "success": True,
                "details": f"Updated employee record with end_date: {last_day}",
            })
        else:
            actions_taken.append({
                "integration": "hris",
                "action": "update_employee",
                "success": False,
                "details": update_result.error,
            })
    except HRISError as e:
        actions_taken.append({
            "integration": "hris",
            "action": "update_employee",
            "success": False,
            "details": str(e),
        })

    # -- Offboarding tasks --
    # Order matters here: equipment return should happen before we cut access.
    # The "revoke all access" task is due ON the last day (0 working days before).
    # TODO: could make these configurable per-team instead of hardcoded
    offboarding_tasks = [
        {
            "title": "Schedule equipment return",
            "description": (
                f"Arrange return of equipment for "
                f"{employee_data['first_name']} {employee_data['last_name']}"
            ),
            "assignee": "it-team@company.com",
            "due_days_before": 2,
            "task_key": "equipment_return",
        },
        {
            "title": "Revoke development tool access",
            "description": (
                f"Revoke GitHub and other dev tool access for "
                f"{employee_data['first_name']} {employee_data['last_name']}"
            ),
            "assignee": "it-team@company.com",
            "due_days_before": 1,
            "task_key": "revoke_dev_tools",
        },
        {
            "title": "Revoke email, Slack, and badge access",
            "description": (
                f"Revoke all remaining access for "
                f"{employee_data['first_name']} {employee_data['last_name']}"
            ),
            "assignee": "it-team@company.com",
            "due_days_before": 0,  # due ON last day
            "task_key": "revoke_all_access",
        },
    ]

    task_count = 0

    for task_def in offboarding_tasks:
        try:
            # same idempotency approach as the new hire workflow
            idempotency_key = f"{event['event_id']}_{task_def['task_key']}"
            existing = it_tasks.find_task_by_metadata(
                "idempotency_key", idempotency_key
            )

            if existing:
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": True,
                    "details": (
                        f"Task {existing.task_id}: {task_def['title']} "
                        f"(already exists, skipped)"
                    ),
                })
                task_count += 1
                continue

            due_date = working_days_before(last_day, task_def["due_days_before"])

            result = it_tasks.create_task(
                title=task_def["title"],
                description=task_def["description"],
                assignee=task_def["assignee"],
                due_date=str(due_date),
                metadata={
                    "event_id": event["event_id"],
                    "idempotency_key": idempotency_key,
                },
            )

            if result.success:
                task = result.task
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": True,
                    "details": (
                        f"Task {task.task_id}: {task_def['title']} "
                        f"(assigned to: {task_def['assignee']}, due: {due_date})"
                    ),
                })
                task_count += 1
            else:
                actions_taken.append({
                    "integration": "it_tasks",
                    "action": "create_task",
                    "success": False,
                    "details": result.error,
                })

        except ITTasksError as e:
            actions_taken.append({
                "integration": "it_tasks",
                "action": "create_task",
                "success": False,
                "details": str(e),
            })

    # -- Build and return result --
    full_name = f"{employee_data['first_name']} {employee_data['last_name']}"
    reason = event.get("reason", "not specified")

    return {
        "event_id": event["event_id"],
        "event_type": "offboarding",
        "status": "completed",
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "actions_taken": actions_taken,
        "summary": (
            f"Offboarding initiated for {full_name} "
            f"({employee_data['team']}, last day {event['last_day']}, "
            f"reason: {reason}). "
            f"Updated employee record and created {task_count} offboarding tasks."
        ),
    }
