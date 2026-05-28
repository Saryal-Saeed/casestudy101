# People Ops Automation — Case Study

## Deliverables Notes

### 1. What was the trickiest part?
The trickiest part was handling the exact date calculation for the offboarding workflow where the "Revoke email, Slack, and badge access" task needs to happen **on** the last day, meaning `days=0` working days before. I had to ensure the `working_days_before()` utility logic could gracefully handle `days=0` without subtracting any days, while other tasks needed 1 or 2 days subtracted, correctly skipping weekends.

Additionally, idempotency was an interesting challenge. Since the mock integration provided a `find_task_by_metadata` method, I decided to construct a unique `idempotency_key` composed of the `event_id` and a predefined `task_key` for each specific task (e.g. `evt_001_order_equipment`). This guarantees we don't accidentally provision duplicate equipment if the webhook/event fires twice.

### 2. What would you add if you had another 2 hours?
- **More granular Error Handling / Retries**: Currently, we catch `HRISError` and `ITTasksError` and gracefully mark the action as `success=False`. If I had more time, I would implement a retry mechanism (e.g., exponential backoff using the `tenacity` library) for transient failures, especially since the mock supports a `failure_rate`.
- **Typing & Models**: I would use `pydantic` models for the incoming event payloads instead of relying solely on the manual dictionary validation in `validator.py`. It provides cleaner code, automatic type casting, and immediate schema validation.
- **Better Logging**: Replace basic `print()` statements in `main.py` with the standard Python `logging` module so we can emit structured JSON logs, which is vital for observability in a real-world People Ops automation system.

### 3. Assumptions made
- I assumed that "working days" strictly meant Monday through Friday, and we did not need to account for specific national or company holidays.
- For offboarding, I assumed that if the employee was not found in the HRIS, we should halt the entire workflow rather than creating IT tasks for an unknown employee.
- I assumed the `event_id` in the input payloads is guaranteed to be globally unique for the purpose of constructing idempotency keys.

## How to run the code
```bash
# Process New Hire
python -m src.main samples/new_hire.json

# Process Offboarding
python -m src.main samples/offboarding.json

# Run tests
python -m src.test_workflows
```
