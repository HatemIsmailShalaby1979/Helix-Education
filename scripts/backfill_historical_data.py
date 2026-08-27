"""
Historical Data Backfill Script.

Extracts historical assessment and competency data from Helix Prime's
operational stores and transforms it into Helix Education EventStore format.
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from state_core.event_models import TopicStartedEvent
from state_core.event_store import EventStore, StoreConfig


def generate_historical_events(days: int = 90):
    """Generates synthetic historical events to simulate a 90-day backfill."""
    events = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    current_date = start_date

    while current_date <= end_date:
        # Simulate daily learning activity for a sample employee
        event = TopicStartedEvent.create(
            topic="RTA_Adherence_Protocol",
            requested_level="intermediate",
            parent_topic=None,
            lesson_title=f"Daily Refresher - {current_date.strftime('%Y-%m-%d')}",
            difficulty="medium",
        )
        # Manually set timestamp to simulate history
        event_dict = event.to_dict()
        event_dict["timestamp"] = current_date.isoformat()
        events.append(event_dict)

        current_date += timedelta(days=1)

    return events


def main():
    days = 90
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1].replace("--days=", ""))
        except ValueError:
            pass

    print(f"[MIGRATING] Starting historical backfill for {days} days...")

    # Initialize EventStore
    config = StoreConfig(path="data/migration_backfill.jsonl")
    store = EventStore(config)

    events = generate_historical_events(days)

    for event_dict in events:
        # In a real scenario, we would use _append_raw to bypass validation for legacy data
        # For this spike, we are generating valid new events with historical timestamps
        line = json.dumps(event_dict) + "\n"
        with open(config.path, "a") as f:
            f.write(line)

    print(f"✅ SUCCESS: Backfilled {len(events)} historical events to {config.path}")
    print("ℹ️  NOTE: In production, this would pull from Helix Prime PostgreSQL via ETL.")


if __name__ == "__main__":
    main()
