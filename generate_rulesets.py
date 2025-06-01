import os
import re
import argparse
import pandas as pd
import yaml

def escape_for_regex(s: str) -> str:
    """
    Escape dots and hyphens so that <group_id>.<artifact_id> becomes
    a literal regex. E.g. 'org.springframework.boot' -> 'org\\.springframework\\.boot'
    """
    return re.escape(s)

def build_ruleset_structure(df: pd.DataFrame) -> dict:
    """
    Given a DataFrame with columns:
      - group_id
      - artifact_id
      - framework
      - category
      - subcategory
    Return a nested dict matching the desired YAML schema.
    """
    ruleset = {"categories": []}
    category_map = {}

    for _, row in df.iterrows():
        cat = row["category"].strip()
        subcat = row["subcategory"].strip()
        fw = row["framework"].strip()
        gid = row["group_id"].strip()
        aid = row["artifact_id"].strip()

        # Skip if any required field is missing or empty
        if not all([cat, subcat, fw, gid, aid]):
            continue

        escaped_group = escape_for_regex(gid)
        escaped_artifact = escape_for_regex(aid)
        pattern = f".*{escaped_group}\\.{escaped_artifact}.*"

        # Build nested maps
        category_map.setdefault(cat, {})
        category_map[cat].setdefault(subcat, {})
        category_map[cat][subcat].setdefault(fw, {"patterns": set()})
        category_map[cat][subcat][fw]["patterns"].add(pattern)

    # Convert nested maps to list structure
    for cat, subcats in sorted(category_map.items()):
        cat_entry = {"name": cat, "subcategories": []}
        for subcat, fws in sorted(subcats.items()):
            subcat_entry = {"name": subcat, "frameworks": []}
            for fw, data in sorted(fws.items()):
                patterns_list = sorted(data["patterns"])
                subcat_entry["frameworks"].append({
                    "name": fw,
                    "patterns": patterns_list
                })
            cat_entry["subcategories"].append(subcat_entry)
        ruleset["categories"].append(cat_entry)

    return ruleset

def write_yaml(ruleset: dict, output_path: str):
    """
    Write a Python dictionary `ruleset` to `output_path` as YAML.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(ruleset, f, sort_keys=False)

def process_csv_file(csv_path: str, output_dir: str):
    """
    Read a single annotated CSV and write one YAML ruleset file.
    """
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    required_cols = {"group_id", "artifact_id", "framework", "category", "subcategory"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"⚠️ Skipping {csv_path}: missing columns {', '.join(sorted(missing))}")
        return

    ruleset = build_ruleset_structure(df)
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    yaml_filename = f"{base_name}.yaml"
    output_path = os.path.join(output_dir, yaml_filename)
    write_yaml(ruleset, output_path)
    print(f"✅ Wrote ruleset: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert annotated CSV(s) into YAML ruleset file(s). "
                    "If input is a directory, processes all .csv files within."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to an annotated CSV file or a directory containing multiple CSVs."
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="rules",
        help="Directory under which to emit YAML rule files."
    )
    args = parser.parse_args()

    input_path = args.input
    output_dir = args.output_dir

    if os.path.isdir(input_path):
        # Process all .csv files in directory (non-recursive)
        for filename in os.listdir(input_path):
            if filename.lower().endswith(".csv"):
                csv_path = os.path.join(input_path, filename)
                process_csv_file(csv_path, output_dir)
    else:
        # Single CSV file
        process_csv_file(input_path, output_dir)

if __name__ == "__main__":
    main()
