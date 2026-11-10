"""Known Hindsight 1.2 default local models and required cached files."""

from config import ROOT

MODELS = {
    "BAAI/bge-small-en-v1.5": ("config.json", "model.safetensors", "tokenizer.json",
                                "tokenizer_config.json", "modules.json", "1_Pooling/config.json"),
    "hindsight-ai/hs-rerank-1": ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"),
}
IGNORE = ["onnx/*", "openvino/*", "*.onnx", "*.bin", "*.h5", "*.msgpack", "*.ot", "*.gguf", "*.tflite"]


def missing_models(cache_root=None):
    hub = (cache_root or ROOT / ".cache/huggingface") / "hub"
    missing = []
    for model, required in MODELS.items():
        repo = hub / ("models--" + model.replace("/", "--"))
        try:
            revision = (repo / "refs/main").read_text().strip()
        except OSError:
            missing.append(model)
            continue
        if not revision or any(not (repo / "snapshots" / revision / name).is_file() for name in required):
            missing.append(model)
    return missing
