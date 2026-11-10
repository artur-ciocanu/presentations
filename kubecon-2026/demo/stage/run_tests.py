"""Run unit tests after the isolated launcher has cleared inherited settings."""

import pytest

raise SystemExit(pytest.main(["-q", "test_config.py", "test_runtime.py", "test_server.py", "test_offline.py", "test_offline_chainlit.py"]))
