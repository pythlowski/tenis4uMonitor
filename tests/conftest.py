import os
import tempfile
import textwrap

import pytest

import logger

# Keep test log output out of the real logs/ directory.
logger.Logger.LOGS_DIRECTORY = tempfile.mkdtemp(prefix="court-monitor-test-logs-")

import settings as settings_module  # noqa: E402
from settings import Settings  # noqa: E402

PREFIX = settings_module.ENV_PREFIX

BASE_TOML = """
fetch_interval_minutes = 20

[discord]
mode = "global"

[[facilities]]
key = "tenis4u_104"
name = "Hala XYZ"
provider = "tenis4u"
facility_id = 104
court_type = "badminton"
"""


@pytest.fixture
def make_settings(tmp_path, monkeypatch):
    """Build Settings from an isolated config.toml and env, ignoring the developer's real files."""

    for name in list(os.environ):
        if name.upper().startswith(PREFIX):
            monkeypatch.delenv(name)

    def factory(toml: str = BASE_TOML, env: dict[str, str] | None = None, **init) -> Settings:
        (tmp_path / "config.toml").write_text(textwrap.dedent(toml), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        env = {f"{PREFIX}DISCORD__GLOBAL_WEBHOOK_URL": "https://discord.test/global"} if env is None else env
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return Settings(_env_file=None, **init)

    return factory
