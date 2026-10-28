"""
Gemini Flow - Faster-Whisper Model Downloader
Downloads Faster-Whisper neural speech weights (small.en, base.en, tiny.en)
to the local models/ directory with resume support and integrity verification.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ModelDownloader")

AVAILABLE_MODELS = {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base.en": "Systran/faster-whisper-base.en",
    "small.en": "Systran/faster-whisper-small.en",
}

def verify_model(target_dir: Path) -> bool:
    """Check if model files exist and are valid."""
    if not target_dir.exists():
        return False
    # model.bin and config.json are strictly required
    for req in ["model.bin", "config.json"]:
        p = target_dir / req
        if not p.exists() or p.stat().st_size == 0:
            return False
    # Vocab/tokenizer must be present
    has_vocab = any(
        (target_dir / f).exists() and (target_dir / f).stat().st_size > 0
        for f in ["vocabulary.txt", "vocabulary.json", "tokenizer.json"]
    )
    return has_vocab

def download_model(model_name: str, output_root: Path) -> bool:
    """Download and place a model into output_root / model_name."""
    if model_name not in AVAILABLE_MODELS:
        logger.error(f"Unknown model name: '{model_name}'. Available: {list(AVAILABLE_MODELS.keys())}")
        return False

    target_dir = output_root / model_name
    if verify_model(target_dir):
        logger.info(f"Model '{model_name}' is already installed and verified at: {target_dir}")
        return True

    logger.info(f"Downloading model '{model_name}' ({AVAILABLE_MODELS[model_name]})...")
    logger.info(f"Destination: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        from faster_whisper import download_model as fw_download
        downloaded_path = fw_download(model_name, output_dir=str(target_dir))
        logger.info(f"Successfully downloaded to: {downloaded_path}")
    except Exception as e:
        logger.warning(f"faster_whisper.download_model failed ({e}), attempting huggingface_hub fallback...")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=AVAILABLE_MODELS[model_name],
                local_dir=str(target_dir),
                local_dir_use_symlinks=False
            )
        except Exception as hf_err:
            logger.error(f"Failed to download '{model_name}': {hf_err}")
            return False

    if verify_model(target_dir):
        logger.info(f"Model '{model_name}' integrity check PASSED!")
        return True
    else:
        logger.error(f"Model '{model_name}' downloaded but failed integrity verification.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download Faster-Whisper models for Gemini Flow.")
    parser.add_argument(
        "--model",
        type=str,
        default="small.en",
        choices=["tiny.en", "base.en", "small.en", "all"],
        help="Model to download (default: small.en)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save models into (default: <project_root>/models)"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    output_root = Path(args.output_dir) if args.output_dir else project_root / "models"
    output_root.mkdir(parents=True, exist_ok=True)

    targets = ["small.en"] if args.model == "small.en" else (list(AVAILABLE_MODELS.keys()) if args.model == "all" else [args.model])

    success_all = True
    for m in targets:
        success = download_model(m, output_root)
        if not success:
            success_all = False

    if success_all:
        logger.info("All requested models downloaded and ready for offline dictation.")
        sys.exit(0)
    else:
        logger.error("One or more model downloads encountered an issue.")
        sys.exit(1)

if __name__ == "__main__":
    main()
