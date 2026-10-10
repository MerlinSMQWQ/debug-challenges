import argparse
import csv
import json
from pathlib import Path
import sys

from settlement_export.diagnostics import stack_probe


def main():
    parser = argparse.ArgumentParser(description="将发票转换为结算记录")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with stack_probe(args.output_dir, "exporter"):
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
                        print(
                            json.dumps({
                                "event": "rejected",
                                "reason": "unsupported_currency",
                                "row": row,
                            }),
                            file=sys.stderr,
                            flush=True,
                        )
                        continue
                    writer.writerow(row)
                    accepted += 1
                    amounts[row["currency"]] += int(row["cents"])
        print(json.dumps({
            "input_count": total,
            "exported_count": accepted,
            "rejected_count": rejected,
            "totals_cents": amounts,
        }), flush=True)


if __name__ == "__main__":
    main()
