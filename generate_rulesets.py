import os
import re
import argparse
import pandas as pd
import yaml

class QuotedDumper(yaml.SafeDumper):
    def represent_str(self, data):
        # If the string contains backslashes or colons, emit it in double‐quoted style
        if "\\" in data or ":" in data:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return super().represent_str(data)

QuotedDumper.add_representer(str, QuotedDumper.represent_str)

def escape_for_regex(s: str) -> str:
    return re.escape(s)

def build_ruleset_structure(df: pd.DataFrame) -> dict:
    ruleset = {"categories": []}
    category_map = {}

    for _, row in df.iterrows():
        cat = row.get("category", "").strip()
        subcat = row.get("subcategory", "").strip()
        fw = row.get("framework", "").strip()
        if not all([cat, subcat, fw]):
            continue

        gid = row.get("group_id", "").strip()
        aid = row.get("artifact_id", "").strip()
        pkg = row.get("package_name", "").strip()

        if gid:
            escaped_group = escape_for_regex(gid)
            if aid:
                escaped_artifact = escape_for_regex(aid)
                identifier = f"{escaped_group}\\:{escaped_artifact}"
            else:
                identifier = escaped_group
        elif pkg:
            identifier = escape_for_regex(pkg)
        else:
            continue

        pattern = f".*{identifier}.*"

        category_map.setdefault(cat, {})
        category_map[cat].setdefault(subcat, {})
        category_map[cat][subcat].setdefault(fw, {"patterns": set()})
        category_map[cat][subcat][fw]["patterns"].add(pattern)

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
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(ruleset, f, Dumper=QuotedDumper, sort_keys=False)

def process_csv_file(csv_path: str, output_subdir: str):
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    if "group_id" in df.columns:
        required_cols = {"group_id", "framework", "category", "subcategory"}
    elif "package_name" in df.columns:
        required_cols = {"package_name", "framework", "category", "subcategory"}
    else:
        print(f"Skipping {csv_path}: missing both 'group_id' and 'package_name'")
        return

    missing = required_cols - set(df.columns)
    if missing:
        print(f"Skipping {csv_path}: missing columns {', '.join(sorted(missing))}")
        return

    os.makedirs(output_subdir, exist_ok=True)
    ruleset = build_ruleset_structure(df)
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    yaml_filename = f"{base_name}.yaml"
    output_path = os.path.join(output_subdir, yaml_filename)
    write_yaml(ruleset, output_path)
    print(f"Wrote ruleset: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert annotated CSV(s) into YAML ruleset file(s). If input is a directory, processes all .csv files recursively."
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Path to a CSV file or a directory containing one or more CSVs.")
    parser.add_argument("-o", "--output-dir", default="rules",
                        help="Base directory under which to emit YAML rule files.")
    args = parser.parse_args()

    input_path = args.input
    output_base = args.output_dir

    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            rel_dir = os.path.relpath(root, input_path)
            target_subdir = output_base if rel_dir == "." else os.path.join(output_base, rel_dir)
            for filename in files:
                if filename.lower().endswith(".csv"):
                    csv_path = os.path.join(root, filename)
                    process_csv_file(csv_path, target_subdir)
    else:
        process_csv_file(input_path, output_base)

if __name__ == "__main__":
    main()
