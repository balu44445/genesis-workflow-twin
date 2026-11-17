import argparse
import json
from pathlib import Path
import sys

from .extract import from_environment
from .model import Snapshot, lower
from .replay import replay
from .verifier import verify
from .install import prepare, check_export


def load(path):
    return json.loads(Path(path).read_text())


def emit(value, output=None):
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text)
    else:
        print(text, end="")


def main():
    parser = argparse.ArgumentParser(prog="genesis")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "model", "replay"):
        command = commands.add_parser(name)
        command.add_argument("snapshot")
        command.add_argument("--out")
        if name == "verify":
            command.add_argument("--bound", type=int, default=3)
            command.add_argument("--timeout-ms", type=int, default=2000)
        if name == "replay":
            command.add_argument("evidence")
    commands.add_parser("extract").add_argument("--out", required=True)
    setup = commands.add_parser("prepare-pdi")
    for actor in ("alice", "bob", "carol"):
        setup.add_argument("--" + actor, required=True)
    setup.add_argument("--out-dir", required=True)
    compare = commands.add_parser("check-install")
    compare.add_argument("snapshot")
    compare.add_argument("expected")
    demo = commands.add_parser("demo")
    demo.add_argument("--out-dir", default="evidence")
    args = parser.parse_args()
    try:
        if args.command == "prepare-pdi":
            emit(prepare(args.alice, args.bob, args.carol, args.out_dir))
            return 0
        if args.command == "check-install":
            emit(check_export(Snapshot.model_validate(load(args.snapshot)),
                              Snapshot.model_validate(load(args.expected))))
            return 0
        if args.command == "extract":
            emit(from_environment().model_dump(), args.out)
            return 0
        if args.command == "demo":
            root = Path(__file__).with_name("static")
            destination = Path(args.out_dir)
            destination.mkdir(parents=True, exist_ok=True)
            summary = {}
            for variant in ("vulnerable", "fixed"):
                snapshot = Snapshot.model_validate(load(root / f"{variant}.json"))
                evidence = verify(snapshot)
                emit(evidence, destination / f"{variant}.json")
                summary[variant] = evidence["status"]
                if variant == "vulnerable" and evidence["status"] == "violation":
                    emit(replay(snapshot, evidence), destination / "replay.json")
            emit(summary)
            return 0 if summary == {"vulnerable": "violation", "fixed": "no_violation_within_bound"} else 3
        snapshot = Snapshot.model_validate(load(args.snapshot))
        if args.command == "verify":
            result = verify(snapshot, args.bound, args.timeout_ms)
            emit(result, args.out)
            return {"violation": 2, "no_violation_within_bound": 0, "inconclusive": 3}[result["status"]]
        if args.command == "model":
            emit(lower(snapshot), args.out)
        else:
            emit(replay(snapshot, load(args.evidence)), args.out)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"GENESIS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
