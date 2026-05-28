# People Ops Automation Hub

## Case Study for Working Student – People Automation

---

## Context

You're joining the People team at a company with ~400 employees. The team handles onboarding, employee changes, and internal requests—currently requiring significant manual work.

**Your task:** Build a small automation script that processes a "new hire" event and creates the right onboarding tasks.

| ⏱ Time | 🛠 Stack | 🎯 Level |
|--------|---------|----------|
| 2–3 hours | Python | Working Student |

---

## The System

Your script receives an event (JSON) and should:
1. **Validate** the input
2. **Execute** the workflow (calling the provided integrations)
3. **Return** a structured result

You can run it however you like — a CLI that reads `samples/new_hire.json`, a `main()` function, a notebook, whatever feels natural.

---

## Required: New Hire Workflow

**Input:** New employee details (see `samples/new_hire.json`)

**What it should do:**
- Validate the input (the required fields are listed below)
- Create the employee record in HRIS
- Create a small set of onboarding tasks in the IT system, each with an owner and a due date calculated from the start date
- Return a structured result (see `expected_outputs/new_hire_output.json`)

**Required input fields:** `event_id`, `type`, `employee.first_name`, `employee.last_name`, `employee.email`, `employee.team`, `employee.start_date`.

**Suggested onboarding tasks** (you can adapt):
- Create email and Slack accounts → due 3 working days before start
- Order equipment (laptop + monitor + headset) → due 5 working days before start
- Schedule Day 1 orientation → due 1 working day before start

---

## Bonus: Offboarding Workflow (optional)

The mirror image of onboarding. When someone leaves, the People team needs accounts revoked, equipment returned, and the HRIS record updated — and the *order* matters (you don't want to cut someone's email on day 1 of their notice period).

**Input:** see `samples/offboarding.json` — employee email, last day, optional reason.

**What it should do:**
- Look up the employee in HRIS (fail clearly if they don't exist)
- Update the HRIS record with an `end_date`
- Create a small set of offboarding tasks in the IT system, with due dates calculated from `last_day`:
  - Schedule equipment return → due 2 working days **before** last day
  - Revoke development tool access (GitHub etc.) → due 1 working day **before** last day
  - Revoke email, Slack, and badge access → due **on** last day
- Return a structured result in the same shape as the New Hire workflow

Same validation and "don't crash on bad input" rules apply.

---

## What We Provide

```
people-automation-working-student-case-study/
├── integrations/         # Mock external services (ready to use)
│   ├── hris.py           # HR Information System
│   ├── it_tasks.py       # IT Task/Ticketing System
│   └── ticketing.py      # People Team Ticketing (not needed for either task)
│
├── samples/              # Example inputs
│   ├── new_hire.json
│   └── offboarding.json  # for the bonus task
│
├── expected_outputs/     # What your output should look like
│   └── new_hire_output.json
│
└── src/                  # YOUR CODE GOES HERE
```

The integrations are plain Python classes — just import and call them. By default they always succeed; you can pass `failure_rate=0.1` to a client if you want to try the optional failure-handling stretch goal.

---

## Expected Output Format

Your script should return a result like this:

```json
{
  "event_id": "evt_001",
  "event_type": "new_hire",
  "status": "completed",
  "processed_at": "2025-01-22T10:30:00Z",

  "actions_taken": [
    {
      "integration": "it_tasks",
      "action": "create_task",
      "success": true,
      "details": "Task IT-A1B2C3: Create email and Slack accounts (assigned to: it-team@company.com, due: 2025-01-29)"
    }
  ],

  "summary": "Onboarding initiated for Lina Müller (Engineering, starting 2025-02-01). Created employee record and 3 onboarding tasks."
}
```

See `expected_outputs/new_hire_output.json` for a full example.

---

## Requirements

### Must Have
- [ ] New Hire workflow runs end-to-end on `samples/new_hire.json`
- [ ] Basic input validation (a missing required field should not crash the script — return a clear error instead)
- [ ] At least one test (any framework, or even a simple `assert` script)

### Nice to Have (pick any if you have time)
- [ ] Handle integration failures without crashing (try `HRISClient(failure_rate=0.1)`)
- [ ] Team-specific tasks (e.g. Engineering also gets a "Grant GitHub access" task)
- [ ] Idempotency: running the same `event_id` twice doesn't create duplicate tasks

---

## Deliverables

1. **Working code** in `src/` — we will run it on the sample input
2. **At least one test**
3. **A short README or comment block** with:
   - What was the trickiest part?
   - What would you add if you had another 2 hours?
   - Any assumptions you made

---

## Tips

- Start with the happy path; don't over-engineer
- The integrations are mocked — just import and call them
- We care more about clear, readable code than about clever code
- It's fine to ask questions — make reasonable assumptions and write them down

---

## Questions?

Reach out to Neil or Moayad.

**Good luck!**
