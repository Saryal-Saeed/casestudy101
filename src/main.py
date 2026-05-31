"""
CLI entry point. Reads a JSON event file and routes it to the right workflow.

Usage: python -m src.main samples/new_hire.json
"""

import json
import sys
from pathlib import Path

from src.workflows import process_new_hire, process_offboarding


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <path_to_json>")
        print("Example: python -m src.main samples/new_hire.json")
        sys.exit(1)

    file_path = Path(sys.argv[1])

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

    # route to the right workflow based on event type
    event_type = event.get("type")

    if event_type == "new_hire":
        result = process_new_hire(event)
    elif event_type == "offboarding":
        result = process_offboarding(event)
    else:
        result = {
            "status": "error",
            "errors": [f"Unknown event type: {event_type}"],
        }

    # ensure_ascii=False so names like "Müller" print correctly
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
