"""
Automated Downloader for whisper.cpp Windows x64 Binaries and GGML Models.
Part of Gemini Flow Ultra-Lightweight Inference Subsystem.
"""
import os
import sys
import zipfile
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WhisperCppDownloader")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models" / "whisper.cpp"
RUNTIME_DIR = PROJECT_ROOT / "runtime" / "whisper.cpp"

WHISPER_CPP_RELEASE_URL = "https://github.com/ggerganov/whisper.cpp/releases/download/v1.7.4/whisper-bin-x64.zip"
GGML_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
GGML_BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"


def download_file(url: str, dest_path: Path, desc: str):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and dest_path.stat().st_size > 10000:
        logger.info(f"{desc} already exists at {dest_path} ({dest_path.stat().st_size} bytes). Skipping.")
        return True

    logger.info(f"Downloading {desc} from {url}...")
    tmp_path = dest_path.with_suffix(".tmp")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                if count % 1000 == 0:
                    logger.info(f"{desc} progress: {percent}% ({count * block_size // 1048576}MB / {total_size // 1048576}MB)")

        urllib.request.urlretrieve(url, tmp_path, reporthook=reporthook)
        if tmp_path.exists():
            if dest_path.exists():
                dest_path.unlink()
            tmp_path.rename(dest_path)
            logger.info(f"Successfully downloaded {desc} to {dest_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download {desc}: {e}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return False


def setup_whisper_cpp(download_model: bool = True):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    zip_dest = RUNTIME_DIR / "whisper-bin-x64.zip"
    cli_exe = RUNTIME_DIR / "whisper-cli.exe"
    main_exe = RUNTIME_DIR / "main.exe"

    if not (cli_exe.exists() or main_exe.exists()):
        ok = download_file(WHISPER_CPP_RELEASE_URL, zip_dest, "whisper.cpp Windows x64 binary")
        if ok and zip_dest.exists():
            try:
                logger.info(f"Extracting {zip_dest} into {RUNTIME_DIR}...")
                with zipfile.ZipFile(zip_dest, "r") as zf:
                    zf.extractall(RUNTIME_DIR)
                logger.info("Extraction complete.")
            except Exception as ex:
                logger.error(f"Error extracting zip: {ex}")

    if download_model:
        model_dest = MODELS_DIR / "ggml-small.bin"
        download_file(GGML_MODEL_URL, model_dest, "GGML small model (ggml-small.bin)")


if __name__ == "__main__":
    logger.info("Starting whisper.cpp automated setup...")
    setup_whisper_cpp()
    logger.info("whisper.cpp setup process completed.")
