# fetch_maven_groups.py
import requests
import csv
import os
import argparse

OUTPUT_DIR = "output"
BASE_URL = "https://search.maven.org/solrsearch/select"
DEFAULT_DEPTH = 3


def collapse_group_id(group_id: str, max_depth: int) -> str:
    parts = group_id.split('.')
    return '.'.join(parts[:max_depth])


def fetch_unique_groups(prefix, depth):
    start = 0
    rows = 100
    seen_groups = set()

    while True:
        params = {
            "q": f"g:{prefix}*",
            "rows": rows,
            "start": start,
            "wt": "json"
        }
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        docs = response.json()["response"]["docs"]

        if not docs:
            break

        for doc in docs:
            full_group = doc["g"]
            collapsed = collapse_group_id(full_group, depth)
            seen_groups.add(collapsed)

        start += rows

    return sorted(seen_groups)


def write_groups_to_csv(groups, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group_id", "category", "subcategory", "framework", "ecosystem"])
        for group in groups:
            writer.writerow([group, "", "", "", ""])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True, help="Group ID prefix (e.g., org.springframework)")
    parser.add_argument("--depth", type=int, default=DEFAULT_DEPTH, help=f"Max depth of groupId (default: {DEFAULT_DEPTH})")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    group_ids = fetch_unique_groups(args.prefix, args.depth)
    print(f"✅ Found {len(group_ids)} unique groupIds")

    outfile = os.path.join(OUTPUT_DIR, f"{args.prefix.replace('.', '_')}_groups.csv")
    write_groups_to_csv(group_ids, outfile)
    print(f"📄 Wrote groups to {outfile}")