"""
Non-interactive Python replacement for unzip_unwrap_move.bat + remove_ds_store.bat +
remove_max.bat + empty.bat.

Unzips every zip in data/raw_data, flattens any data_Q*/data_Q* wrapper nesting,
strips macOS junk (__MACOSX, .DS_Store), moves the resulting per-quarter folders
into 'data/raw data', then deletes the raw_data zip staging directory.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_data"
FINAL = ROOT / "data" / "raw data"


def unzip_all():
    FINAL.mkdir(parents=True, exist_ok=True)
    zips = sorted(RAW.glob("*.zip"))
    if not zips:
        print("No zip files found in", RAW)
        return
    for z in zips:
        target = RAW / z.stem
        print(f"[UNZIP] {z.name}")
        with zipfile.ZipFile(z) as zf:
            zf.extractall(target)


def flatten_wrappers():
    print("\n=== Flattening nested data_Q*/data_Q* folders ===")
    for outer in RAW.glob("data_Q*"):
        if not outer.is_dir():
            continue
        inner_dirs = [d for d in outer.iterdir() if d.is_dir() and d.name.startswith("data_Q")]
        if not inner_dirs:
            continue

        # inner dirs often share the same name as `outer` (the zip wraps itself),
        # so move them to a scratch name first, then delete outer, then rename.
        tmp_paths = []
        for inner in inner_dirs:
            print(f"  Unwrapping {outer.name}/{inner.name}")
            tmp_dest = RAW / f"__unwrap__{inner.name}"
            if tmp_dest.exists():
                shutil.rmtree(tmp_dest)
            shutil.move(str(inner), str(tmp_dest))
            tmp_paths.append((tmp_dest, RAW / inner.name))

        shutil.rmtree(outer, ignore_errors=True)

        for tmp_dest, final_dest in tmp_paths:
            if final_dest.exists():
                shutil.rmtree(final_dest)
            shutil.move(str(tmp_dest), str(final_dest))


def clean_macos_junk():
    print("\n=== Removing __MACOSX folders and .DS_Store files ===")
    for d in RAW.rglob("__MACOSX"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    for f in RAW.rglob(".DS_Store"):
        f.unlink(missing_ok=True)


def move_to_final():
    print("\n=== Moving quarter folders into 'data/raw data' ===")
    for d in RAW.glob("data_Q*"):
        if not d.is_dir():
            continue
        dest = FINAL / d.name
        if dest.exists():
            shutil.rmtree(dest)
        print(f"  {d.name} -> {dest}")
        shutil.move(str(d), str(FINAL))


def cleanup_raw_data():
    print("\n=== Cleaning up data/raw_data ===")
    for z in RAW.glob("*.zip"):
        z.unlink()
    if RAW.exists() and not any(RAW.iterdir()):
        RAW.rmdir()


def main():
    if not RAW.exists():
        raise SystemExit(f"raw_data not found: {RAW}")
    unzip_all()
    flatten_wrappers()
    clean_macos_junk()
    move_to_final()
    cleanup_raw_data()
    print("\nDone.")


if __name__ == "__main__":
    main()
