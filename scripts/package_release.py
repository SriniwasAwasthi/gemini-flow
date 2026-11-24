"""
Gemini Flow - Production Release Packaging Utility
Streams application components directly into dist/Gemini_Flow_Setup_Full.zip
without temporary folder duplication or file lock issues.
"""
import os
import sys
import time
import zipfile
from pathlib import Path

def create_release_archive():
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    zip_path = dist_dir / "Gemini_Flow_Setup_Full.zip"

    print(f"Streaming clean-PC distribution archive to {zip_path}...")
    t0 = time.time()

    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception as e:
            print(f"Notice: removing existing zip: {e}")

    # Files to include at root of zip:
    root_files = [
        dist_dir / "Gemini_Flow_Setup_Full.exe",
        dist_dir / "Gemini_Flow.exe",
        project_root / "app_icon.ico",
        project_root / "app_icon.png",
        project_root / "requirements.txt",
        project_root / "README.md",
        project_root / "Launcher.cs",
        project_root / "main.py",
        project_root / "run.bat",
    ]

    # Directories to include recursively:
    dirs_to_bundle = [
        (project_root / "app", "app"),
        (project_root / "models", "models"),
        (project_root / "runtime", "runtime"),
    ]

    dist_dir.mkdir(parents=True, exist_ok=True)

    # Sensitive personal files that must NEVER be packaged into a public release
    SENSITIVE_FILENAMES = {
        ".credentials.bin",
        "config.json",
        "config.json.bak",
        "config.tmp",
        "history.json",
        "vocabulary.json",
        "metrics.json",
        "profiles.json",
        "gemini_flow.log",
        ".env",
        ".env.local",
    }

    def is_excluded(rel_p: Path, full_p: Path) -> bool:
        parts = rel_p.parts
        for part in parts:
            if part in ("__pycache__", ".git", ".pytest_cache", "recordings"):
                return True
            if part.startswith(".probe_"):
                return True
        name = full_p.name
        if name in SENSITIVE_FILENAMES:
            # Whisper models contain a model config.json which is required for offline inference
            if "models" in parts and name == "config.json":
                return False
            return True
        ext = full_p.suffix.lower()
        if ext in (".pyc", ".pyo", ".log", ".tmp", ".bak", ".wav", ".mp3"):
            return True
        return False

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rf in root_files:
            if rf.exists():
                arcname = rf.name
                zf.write(rf, arcname)
                print(f"  + Root: {arcname}")
            else:
                print(f"  ! Warning: {rf} not found")

        for src_dir, arc_prefix in dirs_to_bundle:
            if not src_dir.exists():
                print(f"  ! Warning: Directory {src_dir} not found!")
                continue
            print(f"  + Bundling {src_dir.name}/ into {arc_prefix}/ (sanitized)...")
            file_count = 0
            excluded_count = 0
            for root, _, files in os.walk(src_dir):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(src_dir)
                    if is_excluded(rel_path, full_path):
                        excluded_count += 1
                        continue
                    arcname = str(Path(arc_prefix) / rel_path)
                    zf.write(full_path, arcname)
                    file_count += 1
            print(f"    Archived {file_count} files from {src_dir.name} (excluded {excluded_count} private/cache files).")

    elapsed = time.time() - t0
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Successfully created {zip_path} ({size_mb:.2f} MB) in {elapsed:.2f}s!")
    return zip_path

if __name__ == "__main__":
    create_release_archive()
