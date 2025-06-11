import requests
import csv
import os

OUTPUT_DIR = "output"
API_URL = "https://api-v2v3search-0.nuget.org/query"
MAX_PACKAGES = 1000

def fetch_top_nuget_packages(limit=1000):
    params = {
        "take": limit,
        "sortBy": "totalDownloads"
    }
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return sorted({pkg["id"] for pkg in data.get("data", [])})

def write_packages_to_csv(packages, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group_id", "category", "subcategory", "framework", "ecosystem"])
        for pkg in packages:
            writer.writerow([pkg, "", "", "", "dotnet"])

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    packages = fetch_top_nuget_packages(MAX_PACKAGES)
    print(f"✅ Fetched {len(packages)} NuGet packages")

    output_file = os.path.join(OUTPUT_DIR, "nuget_packages.csv")
    write_packages_to_csv(packages, output_file)
    print(f"📄 Wrote packages to {output_file}")
