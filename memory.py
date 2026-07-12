from __future__ import annotations

import argparse
import json
from collections import Counter

from ledger import read_events


def _attempts() -> list[dict[str, object]]:
    return read_events(event_type="attempt")


def summary() -> dict[str, object]:
    attempts = _attempts()
    statuses = Counter(event["payload"].get("status", "") for event in attempts)
    families = Counter(
        event["payload"].get("strategy_family", "unspecified") for event in attempts
    )
    return {
        "attempt_count": len(attempts),
        "status_counts": dict(statuses),
        "strategy_family_counts": dict(families),
    }


def search(
    strategy_family: str | None, status: str | None, limit: int
) -> list[dict[str, object]]:
    attempts = _attempts()
    filtered = [
        event
        for event in attempts
        if (strategy_family is None or event["payload"].get("strategy_family") == strategy_family)
        and (status is None or event["payload"].get("status") == status)
    ]
    return filtered[-limit:]


def candidate_history(candidate_id: str) -> list[dict[str, object]]:
    direct = read_events(candidate_id=candidate_id)
    descendants = [
        event
        for event in _attempts()
        if event["payload"].get("parent_candidate") == candidate_id
    ]
    event_ids = {event["id"] for event in direct}
    return direct + [event for event in descendants if event["id"] not in event_ids]


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("summary")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--strategy-family")
    search_parser.add_argument("--status")
    search_parser.add_argument("--limit", type=int, default=20)
    candidate_parser = subparsers.add_parser("candidate")
    candidate_parser.add_argument("candidate_id")
    args = parser.parse_args()

    if args.command == "summary":
        payload: object = summary()
    elif args.command == "search":
        payload = search(args.strategy_family, args.status, args.limit)
    else:
        payload = candidate_history(args.candidate_id)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
