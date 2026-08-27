"""Real-time observability dashboard for the Helix Education Center.

Tails the EventStore and displays a clean auto-refreshing terminal
summary of the learner's mastery progression.

Usage:
    python -m observability.dashboard                  # defaults
    python -m observability.dashboard --path data/events.jsonl
    python -m observability.dashboard --interval 5 --once
"""

import argparse
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from state_core.event_models import (
    LearningStateUpdatedEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)
from state_core.event_store import EventStore, StoreConfig


@dataclass
class DashboardSnapshot:
    """A single point-in-time snapshot of learner progress.

    Inputs:
        total_topics_studied: Number of unique topics the learner
            has engaged with (started, branched to, or passed).
        running_average_score: Latest running average score from the
            event stream.
        topics_mastered: List of topic names where all items are
            passing (from latest LearningStateUpdatedEvent).
        topics_in_progress: List of topics with partial progress.
        total_questions_studied: Cumulative count of answered quiz items.
        events_replayed: Total number of events in the store.
        last_event_timestamp: Timestamp of the most recent event.
        store_path: Path to the JSON Lines event file.
    """

    total_topics_studied: int = 0
    running_average_score: float = 0.0
    topics_mastered: list[str] = field(default_factory=list)
    topics_in_progress: list[str] = field(default_factory=list)
    total_questions_studied: int = 0
    events_replayed: int = 0
    last_event_timestamp: str = ""
    store_path: str = ""


class RealTimeMonitor:
    """Tails the EventStore and produces structured snapshots.

    Reads all events from the store on each tick, extracts the latest
    LearningStateUpdatedEvent for aggregate metrics, and computes
    topic-level statistics from the raw event stream.

    Inputs:
        event_store: An EventStore instance backed by a JSON Lines file.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store
        self._store_path = event_store._config.path  # type: ignore[reportPrivateUsage]

    def snapshot(self) -> DashboardSnapshot:
        """Read the event store and build a current DashboardSnapshot.

        Returns:
            A DashboardSnapshot with the latest metrics.
        """
        events = self._event_store.read_all()

        # ---- Count unique topics studied from raw events ----
        topics_set: set[str] = set()
        for e in events:
            if isinstance(e, TopicStartedEvent):
                topics_set.add(e.topic)
            elif isinstance(e, TopicBranchedEvent):
                topics_set.add(e.parent_topic)
                topics_set.add(e.child_topic)
            elif isinstance(e, TopicPassedEvent):
                topics_set.add(e.topic)

        total_topics_studied = len(topics_set)
        events_replayed = len(events)
        last_ts = events[-1].timestamp if events else ""

        # ---- Extract latest LearningStateUpdatedEvent ----
        latest_update: LearningStateUpdatedEvent | None = None
        for e in events:
            if isinstance(e, LearningStateUpdatedEvent):
                latest_update = e

        if latest_update is not None:
            return DashboardSnapshot(
                total_topics_studied=total_topics_studied,
                running_average_score=latest_update.running_average_score,
                topics_mastered=list(latest_update.topics_mastered),
                topics_in_progress=list(latest_update.topics_in_progress),
                total_questions_studied=latest_update.total_questions_studied,
                events_replayed=events_replayed,
                last_event_timestamp=last_ts,
                store_path=self._store_path,
            )

        # Fallback: no LearningStateUpdatedEvent yet — return zeros
        return DashboardSnapshot(
            total_topics_studied=total_topics_studied,
            events_replayed=events_replayed,
            last_event_timestamp=last_ts,
            store_path=self._store_path,
        )

    def refresh(self, interval: float = 3.0, max_ticks: int | None = None) -> None:
        """Continuously refresh the dashboard in the terminal.

        Clears the screen and re-renders on each tick.

        Inputs:
            interval: Seconds between refreshes (default 3.0).
            max_ticks: Maximum number of refreshes before exiting
                (None = run forever, stop with Ctrl+C).
        """
        ticks = 0
        try:
            while max_ticks is None or ticks < max_ticks:
                self._render()
                time.sleep(interval)
                ticks += 1
        except KeyboardInterrupt:
            self._print_shutdown()

    def _render(self) -> None:
        """Clear the screen and print a single dashboard frame."""
        snap = self.snapshot()
        self._clear_screen()
        self._print_header()
        self._print_metrics(snap)
        self._print_topics(snap)
        self._print_footer(snap)

    @staticmethod
    def _clear_screen() -> None:
        """Cross-platform terminal clear."""
        cmd = ["cmd", "/c", "cls"] if os.name == "nt" else ["clear"]
        subprocess.run(
            cmd,
            check=False,
            shell=False,
        )

    @staticmethod
    def _print_header() -> None:
        """Print the dashboard title bar."""
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        width = 62
        print("┌" + "─" * width + "┐")
        print(f"│  {'HELIX EDUCATION — REAL-TIME MASTERY DASHBOARD'.center(width - 4)}  │")
        print(f"│  {now.center(width - 4)}  │")
        print("├" + "─" * width + "┤")

    @staticmethod
    def _print_metrics(snap: DashboardSnapshot) -> None:
        """Print the core numeric metrics section."""
        print(f"│  Topics Studied:        {str(snap.total_topics_studied).ljust(33)}│")
        print(f"│  Total Questions Done:  {str(snap.total_questions_studied).ljust(33)}│")
        print(f"│  Running Avg Score:     {f'{snap.running_average_score:.4f}'.ljust(33)}│")
        print(f"│  Topics Mastered:       {str(len(snap.topics_mastered)).ljust(33)}│")
        print(f"│  Topics In Progress:    {str(len(snap.topics_in_progress)).ljust(33)}│")

    @staticmethod
    def _print_topics(snap: DashboardSnapshot) -> None:
        """Print the mastered and in-progress topic lists."""
        width = 62
        print("├" + "─" * width + "┤")
        mastered_str = ", ".join(snap.topics_mastered) if snap.topics_mastered else "(none)"
        in_progress_str = ", ".join(snap.topics_in_progress) if snap.topics_in_progress else "(none)"
        label_m = "Mastered:"
        label_i = "In-Progress:"
        filler_m = " " * (width - len(label_m) - len(mastered_str) - 4)
        filler_i = " " * (width - len(label_i) - len(in_progress_str) - 4)
        # Truncate if too long
        if len(mastered_str) > width - 14:
            mastered_str = mastered_str[: width - 17] + "..."
        if len(in_progress_str) > width - 14:
            in_progress_str = in_progress_str[: width - 17] + "..."
        print(f"│  {label_m} {mastered_str}{' ' * (width - len(label_m) - len(mastered_str) - 4)}│")
        print(f"│  {label_i} {in_progress_str}{' ' * (width - len(label_i) - len(in_progress_str) - 4)}│")

    @staticmethod
    def _print_footer(snap: DashboardSnapshot) -> None:
        """Print the footer with event log metadata."""
        width = 62
        print("├" + "─" * width + "┤")
        print(f"│  Event Log:  {snap.store_path.ljust(48)}│")
        print(f"│  Replayed:   {str(snap.events_replayed).ljust(48)}│")
        print(f"│  Last Event: {snap.last_event_timestamp.ljust(46)}│")
        print("└" + "─" * width + "┘")
        print("  Refreshing every 3s · Ctrl+C to stop")

    @staticmethod
    def _print_shutdown() -> None:
        """Print a clean shutdown message."""
        print("\n  Dashboard stopped. ✓")


# ── Standalone entry point ─────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Real-time mastery dashboard for Helix Education Center",
    )
    parser.add_argument(
        "--path",
        default="helix_events.jsonl",
        help="Path to the JSON Lines event file (default: helix_events.jsonl)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Refresh interval in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print a single snapshot and exit (no auto-refresh)",
    )
    return parser


def main() -> None:
    """Run the real-time dashboard as a standalone script."""
    parser = _build_parser()
    args = parser.parse_args()

    config = StoreConfig(path=args.path)
    store = EventStore(config)
    monitor = RealTimeMonitor(store)

    if args.once:
        snap = monitor.snapshot()
        monitor._clear_screen()
        monitor._print_header()
        monitor._print_metrics(snap)
        monitor._print_topics(snap)
        monitor._print_footer(snap)
        print()  # trailing newline
    else:
        try:
            monitor.refresh(interval=args.interval)
        except KeyboardInterrupt:
            monitor._print_shutdown()


if __name__ == "__main__":
    main()
