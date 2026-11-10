"""Explicit preparation-only download; normal demo processes stay offline to Hugging Face."""

import os
import sys

# Set before importing huggingface_hub; this recipe alone permits model downloads.
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
# Model preparation does not need the Azure credential.
os.environ.pop("LLM_API_KEY", None)

from huggingface_hub import snapshot_download

from model_cache import IGNORE, MODELS, missing_models


def main():
    for model in MODELS:
        try:
            snapshot_download(model, ignore_patterns=IGNORE)
            print(f"Cached: {model}", flush=True)
        except Exception as exc:
            sys.exit(f"Could not cache {model}: {type(exc).__name__}")
    missing = missing_models()
    if missing:
        sys.exit("Model cache incomplete: " + ", ".join(missing))
    print("Model cache ready. Normal demo commands use Hugging Face offline mode.")


if __name__ == "__main__":
    main()
