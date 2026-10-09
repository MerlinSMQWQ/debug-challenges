import argparse
import csv
import faulthandler
import json
from pathlib import Path
import signal
import sys


def main():
    parser = argparse.ArgumentParser(description="Export invoices for settlement")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "exporter.stack").open("a") as trace:
        faulthandler.register(signal.SIGUSR1, file=trace, all_threads=True)
        with args.input.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            with (args.output_dir / "exported.csv").open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
                writer.writeheader()
                total = accepted = rejected = 0
                amounts = {currency: 0 for currency in config["currencies"]}
                for row in reader:
                    total += 1
                    if row["currency"] not in amounts:
                        rejected += 1
                        print(json.dumps({"event": "rejected", "reason": "unsupported_currency", "row": row}), file=sys.stderr, flush=True)
                        continue
                    writer.writerow(row)
                    accepted += 1
                    amounts[row["currency"]] += int(row["cents"])
        print(json.dumps({"input_count": total, "exported_count": accepted, "rejected_count": rejected, "totals_cents": amounts}), flush=True)
        faulthandler.unregister(signal.SIGUSR1)


if __name__ == "__main__":
    main()
