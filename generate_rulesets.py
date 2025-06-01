import os
import re
import argparse
import pandas as pd
import yaml

def escape_for_regex(s: str) -> str:
    """
    Escape dots, hyphens, and other regex metacharacters so that identifiers become literal.
    """
    return re.escape(s)

def build_ruleset_structure(df: pd.DataFrame) -> dict:
    """
    Given a DataFrame with columns:
      - For Java: group_id (always), artifact_id (optional), framework, category, subcategory
      - For other ecosystems: package_name, framework, category, subcategory
    Return a nested dict matching the desired YAML schema.
    """
    ruleset = {"categories": []}
    category_map = {}

    for _, row in df.iterrows():
        cat = row.get("category", "").strip()
        subcat = row.get("subcategory", "").strip()
        fw = row.get("framework", "").strip()
        if not all([cat, subcat, fw]):
            # skip rows missing category, subcategory, or framework
            continue

        gid = row.get("group_id", "").strip()
        aid = row.get("artifact_id", "").strip()
        pkg = row.get("package_name", "").strip()

        if gid:
            # Java case (group_id always present). If artifact_id exists, match "group_id.artifact_id"; otherwise match just "group_id".
            escaped_group = escape_for_regex(gid)
            if aid:
                escaped_artifact = escape_for_regex(aid)
                identifier = f"{escaped_group}\\.{escaped_artifact}"
            else:
                identifier = escaped_group
        elif pkg:
            # Non-Java: match full package_name literally
            identifier = escape_for_regex(pkg)
        else:
            # Neither group_id nor package_name present
            continue

        pattern = f".*{identifier}.*"

        # Build nested maps
        category_map.setdefault(cat, {})
        category_map[cat].setdefault(subcat, {})
        category_map[cat][subcat].setdefault(fw, {"patterns": set()})
        category_map[cat][subcat][fw]["patterns"].add(pattern)

    # Convert nested maps to the required list-of-dicts structure
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
    Write the Python dictionary `ruleset` to `output_path` as YAML.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(ruleset, f, sort_keys=False)

def process_csv_file(csv_path: str, output_subdir: str):
    """
    Read a single annotated CSV and write one YAML ruleset file.
    """
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    # Determine which columns must exist
    if "group_id" in df.columns:
        # Java CSV: group_id mandatory, artifact_id optional
        required_cols = {"group_id", "framework", "category", "subcategory"}
    elif "package_name" in df.columns:
        # Non-Java CSV
        required_cols = {"package_name", "framework", "category", "subcategory"}
    else:
        print(f"⚠️  Skipping {csv_path}: missing both 'group_id' and 'package_name'")
        return

    missing = required_cols - set(df.columns)
    if missing:
        print(f"⚠️  Skipping {csv_path}: missing columns {', '.join(sorted(missing))}")
        return

    ruleset = build_ruleset_structure(df)
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    yaml_filename = f"{base_name}.yaml"
    output_path = os.path.join(output_subdir, yaml_filename)
    write_yaml(ruleset, output_path)
    print(f"  Wrote ruleset: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert annotated CSV(s) into YAML ruleset file(s). "
                    "If input is a directory, processes all .csv files recursively."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to a CSV file or a directory containing one or more CSVs."
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="rules",
        help="Base directory under which to emit YAML rule files."
    )
    args = parser.parse_args()

    input_path = args.input
    output_base = args.output_dir

    if os.path.isdir(input_path):
        # Walk entire directory tree
        for root, _, files in os.walk(input_path):
            rel_dir = os.path.relpath(root, input_path)
            # Preserve folder structure under output_base
            target_subdir = output_base if rel_dir == "." else os.path.join(output_base, rel_dir)
            for filename in files:
                if filename.lower().endswith(".csv"):
                    csv_path = os.path.join(root, filename)
                    process_csv_file(csv_path, target_subdir)
    else:
        # Single CSV file → write directly under output_base
        process_csv_file(input_path, output_base)

if __name__ == "__main__":
    main()
