"""
Command Line Entry Point for People Ops Automation.

This script parses command-line arguments, reads an input JSON file,
routes the event to the appropriate workflow, and prints the result.
"""

import json
import sys
from pathlib import Path

from src.workflows import process_new_hire, process_offboarding


def main():
    # --- Check for arguments ---
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <path_to_json>")
        print("Example: python -m src.main samples/new_hire.json")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    # --- Read the file ---
    if not file_path.exists():
        print(f"Error: File not found -> {file_path}")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            event = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)

    # --- Route to workflow ---
    event_type = event.get("type")

    if event_type == "new_hire":
        result = process_new_hire(event)
    elif event_type == "offboarding":
        result = process_offboarding(event)
    else:
        # We don't know how to process this event type
        result = {
            "status": "error",
            "errors": [f"Unknown event type: {event_type}"],
        }

    # --- Print result cleanly ---
    # ensure_ascii=False ensures names like 'Müller' print correctly
    # indent=2 makes the output readable for humans
    print(json.dumps(result, indent=2, ensure_ascii=False))


# This magic block ensures main() only runs if you execute this file directly.
# If another file says `from src.main import main`, it won't run automatically.
if __name__ == "__main__":
    main()
