"""
Workflow implementations for People Ops Automation.

This module contains the core business logic for processing HR events:
  - process_new_hire:    Handles onboarding a new employee
  - process_offboarding: Handles employee departure (bonus)

Design decisions:
  - Each workflow is a plain function (not a class) because each call is
    a stateless, one-shot operation.  Functions are simpler and easier to test.
  - Integration clients are passed as optional parameters so tests can
    inject shared instances (dependency injection pattern).
  - Every integration call is wrapped in try/except so a flaky service
    doesn't crash the entire workflow — we record successes AND failures
    in the actions_taken list for a clear audit trail.
  - Idempotency is enforced via metadata keys: before creating a task,
    we check if one with the same idempotency_key already exists.
"""

from datetime import datetime

from integrations.hris import HRISClient, HRISError
from integrations.it_tasks import ITTasksClient, ITTasksError
from src.validator import validate_new_hire, validate_offboarding
from src.date_utils import parse_date, working_days_before


# ---------------------------------------------------------------------------
#  New Hire Workflow
# ---------------------------------------------------------------------------

def process_new_hire(
    event: dict,
    hris: HRISClient | None = None,
    it_tasks: ITTasksClient | None = None,
) -> dict:
    """
    Process a new_hire event end-to-end.

    Steps:
        1. Validate input fields
        2. Create the employee record in HRIS
        3. Create onboarding tasks in the IT system
        4. Return a structured result

    Args:
        event:    The raw event dictionary loaded from JSON.
        hris:     Optional HRISClient (pass one in for testing).
        it_tasks: Optional ITTasksClient (pass one in for testing).

    Returns:
        A result dictionary matching the expected output format.
    """

    # ------------------------------------------------------------------
    # Step 1 — Validate
    #   Call our validator. If it returns any errors, stop here and
    #   return an "error" result instead of crashing.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Step 2 — Set up integration clients
    #   If the caller didn't inject clients, create fresh ones.
    #   This is the "dependency injection" pattern — makes testing easy
    #   because tests can pass shared clients whose state persists.
    # ------------------------------------------------------------------
    if hris is None:
        hris = HRISClient()
    if it_tasks is None:
        it_tasks = ITTasksClient()

    employee = event["employee"]
    start_date = parse_date(employee["start_date"])

    # This list will accumulate a "receipt" of everything we did.
    actions_taken = []

    # ------------------------------------------------------------------
    # Step 3 — Create employee in HRIS
    #   Wrapped in try/except so a flaky HRIS doesn't kill the workflow.
    #   We record the outcome either way.
    # ------------------------------------------------------------------
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
            # The HRIS returned a business error (e.g. "already exists").
            # Not a crash — just log it and keep going.
            actions_taken.append({
                "integration": "hris",
                "action": "create_employee",
                "success": False,
                "details": hris_result.error,
            })
    except HRISError as e:
        # The HRIS service itself blew up (network error, etc.).
        actions_taken.append({
            "integration": "hris",
            "action": "create_employee",
            "success": False,
            "details": str(e),
        })

    # ------------------------------------------------------------------
    # Step 4 — Define onboarding tasks
    #   Each task is a dict with the info we need to create it.
    #   task_key is used for idempotency (see Step 5).
    # ------------------------------------------------------------------

    # Build the equipment description from the event's equipment data.
    equipment = event.get("equipment", {})
    equipment_parts = []
    if equipment.get("laptop"):
        # laptop can be a string ("MacBook Pro 14"") or True
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

    # --- Nice-to-Have #2: Team-specific tasks ---
    # Engineering employees also need GitHub access.
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

    # ------------------------------------------------------------------
    # Step 5 — Create each task in the IT system
    #   For each task definition:
    #     a) Check idempotency — does a task with this key already exist?
    #     b) If not, calculate the due date and create the task.
    #     c) Wrap in try/except for resilience.
    # ------------------------------------------------------------------
    task_count = 0

    for task_def in onboarding_tasks:
        try:
            # --- Nice-to-Have #3: Idempotency check ---
            # Build a unique key from event_id + task_key.
            # If a task with this key exists, skip creation.
            idempotency_key = f"{event['event_id']}_{task_def['task_key']}"
            existing = it_tasks.find_task_by_metadata("idempotency_key", idempotency_key)

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

            # Calculate due date using our working-day utility.
            due_date = working_days_before(start_date, task_def["due_days_before"])

            result = it_tasks.create_task(
                title=task_def["title"],
                description=task_def["description"],
                assignee=task_def["assignee"],
                due_date=str(due_date),  # date → "2025-01-29"
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

    # ------------------------------------------------------------------
    # Step 6 — Build and return the structured result
    # ------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
#  Offboarding Workflow (Bonus)
# ---------------------------------------------------------------------------

def process_offboarding(
    event: dict,
    hris: HRISClient | None = None,
    it_tasks: ITTasksClient | None = None,
) -> dict:
    """
    Process an offboarding event end-to-end.

    Steps:
        1. Validate input fields
        2. Look up the employee in HRIS (fail clearly if not found)
        3. Update the HRIS record with an end_date
        4. Create offboarding tasks in the IT system
        5. Return a structured result

    Args:
        event:    The raw event dictionary loaded from JSON.
        hris:     Optional HRISClient (pass one in for testing).
        it_tasks: Optional ITTasksClient (pass one in for testing).

    Returns:
        A result dictionary matching the expected output format.
    """

    # --- Step 1: Validate ---
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

    # --- Step 2: Set up clients ---
    if hris is None:
        hris = HRISClient()
    if it_tasks is None:
        it_tasks = ITTasksClient()

    employee_email = event["employee_email"]
    last_day = parse_date(event["last_day"])
    actions_taken = []

    # --- Step 3: Look up the employee ---
    # The instructions say "fail clearly if they don't exist".
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

    # --- Step 4: Update HRIS record with end_date ---
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

    # --- Step 5: Create offboarding tasks ---
    # Note the order matters: equipment return first, email/badge last.
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
            "due_days_before": 0,  # Due ON last day
            "task_key": "revoke_all_access",
        },
    ]

    task_count = 0

    for task_def in offboarding_tasks:
        try:
            # Idempotency check
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

    # --- Step 6: Build result ---
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
