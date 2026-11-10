import pytest
from huggingface_hub import constants, hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError


def test_huggingface_client_rejects_uncached_download_in_offline_mode():
    assert constants.HF_HUB_OFFLINE is True
    with pytest.raises(LocalEntryNotFoundError):
        hf_hub_download("stage-offline-test/uncached-model", "model.safetensors")
