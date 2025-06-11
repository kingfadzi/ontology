# Dependency Categorization 

1. **Fetch group IDs (depth 3):**

   ```bash
   python fetch_maven_groups.py --prefix org.springframework --depth 3
   ```

2. **Edit** `output/org_springframework_groups.csv`: add columns

   ```plaintext
   category, subcategory, framework, ecosystem, fetch_artifacts
   ```

3. **Fetch + annotate artifacts:**

   ```bash
   python fetch_annotated_artifacts.py \
     --groups-csv output/org_springframework_groups.csv \
     --output-dir output/artifacts --merge
   ```

4. **Edit** `output/artifacts/all_artifacts.csv`: verify/fix

   ```plaintext
   category, subcategory, framework
   ```

5. **Generate YAML rules (single CSV or folder):**

   ```bash
   python csv_to_ruleset_yaml.py --input output/artifacts \
     --output-dir config/category_rules/java
   ```
