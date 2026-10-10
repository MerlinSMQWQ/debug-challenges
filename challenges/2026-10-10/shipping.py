"""Read a shipping batch and create the carrier's import file."""
import argparse
import csv
import json
from pathlib import Path


class OrderBatch:
    def __init__(self, rows):
        self._rows = list(rows)

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, index):
        try:
            return self._rows[index]
        except IndexError:
            return None


def load_batch(path):
    return OrderBatch(json.loads(Path(path).read_text(encoding="utf-8")))


def preview(batch):
    print("orders={}".format(len(batch)))
    for index in range(min(3, len(batch))):
        print(json.dumps(batch[index], ensure_ascii=False))


def export(batch, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    count = units = 0
    with (output / "manifest.csv.part").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["order_id", "sku", "quantity"])
        for order in batch:
            writer.writerow([order["order_id"], order["sku"], order["quantity"]])
            count += 1
            units += order["quantity"]
            print("packed {}".format(order["order_id"]))
    (output / "manifest.csv.part").replace(output / "manifest.csv")
    (output / "summary.json").write_text(
        json.dumps({"orders": count, "units": units}) + "\n", encoding="utf-8")
    print("completed orders={} units={}".format(count, units))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preview", "export"])
    parser.add_argument("--input", default="data/morning.json")
    parser.add_argument("--output", default="runtime/morning")
    args = parser.parse_args()
    batch = load_batch(args.input)
    if args.command == "preview":
        preview(batch)
    else:
        export(batch, args.output)


if __name__ == "__main__":
    main()
