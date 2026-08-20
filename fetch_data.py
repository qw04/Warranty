from pathlib import Path
import urllib3

BASE_URL = "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data"
DEST_DIR = Path("data/raw_data")

# Create destination directory
DEST_DIR.mkdir(parents=True, exist_ok=True)

http = urllib3.PoolManager(
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=urllib3.Timeout(connect=5.0, read=60.0),
    retries=False
)

quarters = range(1, 5)   # Q1–Q4
years = range(21, 23)    # 2021–2022 (reduced sample: recent, better SMART coverage, larger fleet)

for i in quarters:
    for ab in years:
        filename = f"data_Q{i}_20{ab}.zip"
        url = f"{BASE_URL}/{filename}"
        dest = DEST_DIR / filename

        if dest.exists():
            print(f"[SKIP] {filename}")
            continue

        print(f"[DOWNLOADING] {filename}")

        try:
            with http.request("GET", url, preload_content=False) as r:
                if r.status != 200:
                    print(f"  [ERROR] HTTP {r.status} for {filename}")
                    continue

                expected_size = r.headers.get("Content-Length")
                expected_size = int(expected_size) if expected_size else None

                with open(dest, "wb") as f:
                    for chunk in r.stream(8192):
                        if chunk:
                            f.write(chunk)

            actual_size = dest.stat().st_size
            if expected_size is not None and actual_size != expected_size:
                dest.unlink()
                print(f"  [FAILED] {filename}: truncated download "
                      f"({actual_size} of {expected_size} bytes) - removed, will retry next run")
                continue

            print(f"  [DONE] {filename}")

        except Exception as e:
            if dest.exists():
                dest.unlink()
            print(f"  [FAILED] {filename}: {e}")
