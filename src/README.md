# People Ops Automation Case Study

This is my submission for the Working Student People Automation case study. I've built the script to handle new hires and offboarding requests. I tried to keep it simple and readable without over engineering things.

## Notes on the Deliverables

### 1. What was the trickiest part?
For me, the hardest part was definitely figuring out the exact date calculations for offboarding. There's a task to "Revoke email, Slack, and badge access" that has to happen exactly on the employee's last day. That means calculating for `days=0` working days before. I had to tweak my `working_days_before()` function to make sure that if I pass in 0, it just gives me the same date back and doesn't accidentally subtract a day.

Also, handling idempotency was a fun challenge. I saw the mock IT system has a `find_task_by_metadata` function, so I decided to use a custom `idempotency_key` made by combining the `event_id` and a specific string for each task (like `evt_001_order_equipment`). That way, if we run the script twice on the same event, it won't order two laptops for the same person!

### 2. What would you add if you had another 2 hours?
- **Better error retries**: Right now, if the HRIS or IT system throws an error, my code just logs it as a failure (`success=False`). In real life, if the server is just temporarily down, we should probably retry the request a few times. I'd love to add something like the `tenacity` library to do automatic retries with exponential backoff.
- **Data validation models**: In my `validator.py`, I'm just manually checking if keys exist in the dictionary. If I had more time, I'd use `pydantic`. It would make validating the input much cleaner and give us better error messages if something is wrong.
- **Real logging**: I just used simple `print()` statements in `main.py` to output errors or results. In a production environment, I know we'd need to use the Python `logging` module so logs can be saved in a standard format (like JSON) and searched in tools like Datadog.

### 3. Assumptions I made
- I assumed "working days" strictly meant Monday to Friday. I didn't add any logic for public holidays since we'd need a whole holiday calendar for that.
- During the offboarding process, if the employee email isn't found in the HRIS mock, the script completely stops and returns an error. I assumed we shouldn't create IT revocation tasks for someone who doesn't seem to exist.
- I assumed the `event_id` we get in the JSON files will always be unique. If two events somehow had the same ID, my idempotency logic would think they were the same event and skip creating tasks.

## How to run my code

You can run the script from the command line like this:

```bash
# To run the New Hire workflow
python -m src.main samples/new_hire.json

# To run the Offboarding workflow
python -m src.main samples/offboarding.json

# To run the automated tests I wrote
python -m src.test_workflows
```

Thanks for reviewing my code, and I'm really looking forward to discussing it during the Interview!
