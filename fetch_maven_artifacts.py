import pandas as pd
import requests
import os
import argparse

def fetch_group_artifacts(group_id):
    rows = []
    start = 0
    base_url = "https://search.maven.org/solrsearch/select"

    while True:
        params = {
            "q": f'g:"{group_id}"',
            "rows": 100,
            "start": start,
            "wt": "json"
        }
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json().get("response", {})
        docs = data.get("docs", [])

        if not docs:
            break

        for doc in docs:
            rows.append({
                "group_id": doc.get("g"),
                "artifact_id": doc.get("a"),
                "version": doc.get("latestVersion", ""),
                "description": doc.get("description", "")
            })

        start += 100
        if start >= data.get("numFound", 0):
            break

    return pd.DataFrame(rows)

def fetch_and_annotate(groups_csv: str, output_dir="output/artifacts", merge=True):
    os.makedirs(output_dir, exist_ok=True)
    groups_df = pd.read_csv(groups_csv).fillna("")

    # Normalize fetch_artifacts column to lowercase string for filtering
    if "fetch_artifacts" not in groups_df.columns:
        raise ValueError("Missing 'fetch_artifacts' column in input CSV")

    target_groups = groups_df[groups_df["fetch_artifacts"].astype(str).str.lower() == "true"]
    result_dfs = []

    for _, row in target_groups.iterrows():
        group_id = row["group_id"]
        print(f"📦 Fetching artifacts for: {group_id}")
        artifacts_df = fetch_group_artifacts(group_id)

        for col in ["category", "subcategory", "framework", "ecosystem"]:
            artifacts_df[col] = row.get(col, "")

        result_dfs.append(artifacts_df)

        if not merge:
            out_path = os.path.join(output_dir, f"artifacts_{group_id.replace('.', '_')}.csv")
            artifacts_df.to_csv(out_path, index=False)
            print(f"✅ Wrote: {out_path}")

    if merge and result_dfs:
        merged = pd.concat(result_dfs, ignore_index=True)
        merged_path = os.path.join(output_dir, "all_artifacts.csv")
        merged.to_csv(merged_path, index=False)
        print(f"📄 Merged output: {merged_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and annotate artifacts for selected Spring group IDs.")
    parser.add_argument("--groups-csv", required=True, help="Path to the input CSV of annotated Spring group IDs")
    parser.add_argument("--output-dir", default="output/artifacts", help="Directory to write artifact CSVs")
    parser.add_argument("--merge", action="store_true", help="If set, generate a single merged CSV of all artifacts")
    args = parser.parse_args()

    fetch_and_annotate(args.groups_csv, output_dir=args.output_dir, merge=args.merge)