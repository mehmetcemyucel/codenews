import importlib

import src.config as config_module


def test_env_override_updates_config(monkeypatch):
    """KEYWORDS should follow runtime overrides for flexible deployments."""
    monkeypatch.setenv("KEYWORDS", "ai,ml,devops")

    reloaded = importlib.reload(config_module)
    assert reloaded.Config.KEYWORDS == ["ai", "ml", "devops"]

    # Clean up so other tests read defaults
    monkeypatch.delenv("KEYWORDS", raising=False)
    importlib.reload(config_module)
