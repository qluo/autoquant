from __future__ import annotations

import argparse

from ledger import append_event


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_id")
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    event_id = append_event(
        "promotion",
        {"approval_id": args.approval_id, "reason": args.reason},
        candidate_id=args.candidate_id,
    )
    print(f"recorded promotion event {event_id}")


if __name__ == "__main__":
    main()
