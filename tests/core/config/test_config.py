from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from merlin.core.config.loader import load_config
from merlin.core.config.models import MerlinConfig


@pytest.fixture
def yaml_config_file(tmp_path: Path) -> Path:
    config = {
        "db": {
            "host": "db.example.com",
            "port": 5433,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
            "pool_min_size": 1,
            "pool_max_size": 5,
        },
        "scheduler": {
            "poll_interval_seconds": 120.0,
            "batch_size": 100,
        },
        "worker": {
            "poll_interval_seconds": 2.0,
            "heartbeat_interval_seconds": 10.0,
            "max_concurrent_tasks": 3,
        },
        "reaper": {
            "poll_interval_seconds": 15.0,
            "stale_threshold_seconds": 45.0,
            "max_retries": 5,
        },
        "logging": {
            "level": "DEBUG",
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(config))
    return path


@pytest.fixture
def clean_merlin_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    import os

    for key in list(os.environ):
        if key.startswith("MERLIN__"):
            monkeypatch.delenv(key)
    yield


@pytest.mark.usefixtures("clean_merlin_env")
class TestLoadConfig:
    def test_load_from_yaml(self, yaml_config_file: Path) -> None:
        config = load_config(yaml_config_file)

        assert config.db.host == "db.example.com"
        assert config.db.port == 5433
        assert config.db.database == "testdb"
        assert config.scheduler.poll_interval_seconds == 120.0
        assert config.scheduler.batch_size == 100
        assert config.worker.poll_interval_seconds == 2.0
        assert config.worker.max_concurrent_tasks == 3
        assert config.reaper.stale_threshold_seconds == 45.0
        assert config.reaper.max_retries == 5
        assert config.logging.level == "DEBUG"

    def test_defaults_when_no_file(self) -> None:
        config = load_config(None)

        assert config.db.host == "localhost"
        assert config.db.port == 5432
        assert config.db.database == "merlin"
        assert config.scheduler.poll_interval_seconds == 60.0
        assert config.worker.poll_interval_seconds == 5.0
        assert config.reaper.poll_interval_seconds == 30.0
        assert config.logging.level == "INFO"

    def test_defaults_when_file_missing(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.yaml")

        assert config.db.host == "localhost"

    def test_env_var_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MERLIN__DB__HOST", "env-host")
        monkeypatch.setenv("MERLIN__DB__PORT", "9999")
        monkeypatch.setenv("MERLIN__WORKER__POLL_INTERVAL_SECONDS", "1.0")

        config = load_config(None)

        assert config.db.host == "env-host"
        assert config.db.port == 9999
        assert config.worker.poll_interval_seconds == 1.0

    def test_env_overrides_yaml(
        self, yaml_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MERLIN__DB__HOST", "override-host")

        config = load_config(yaml_config_file)

        assert config.db.host == "override-host"
        assert config.db.port == 5433  # yaml value preserved

    def test_dsn_property(self) -> None:
        config = load_config(None)

        assert config.db.dsn == ("postgresql+asyncpg://merlin:merlin@localhost:5432/merlin")

    def test_invalid_yaml_field(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(yaml.dump({"db": {"port": "not-a-number"}}))

        with pytest.raises(Exception):  # noqa: B017
            load_config(path)

    def test_model_is_pydantic(self) -> None:
        config = load_config(None)

        assert isinstance(config, MerlinConfig)
        serialized = config.model_dump()
        assert "db" in serialized
        assert "scheduler" in serialized

    def test_default_yaml_file_loads(self) -> None:
        default_path = Path(__file__).parents[3] / "config" / "default.yaml"
        config = load_config(default_path)

        assert config.db.host == "localhost"
        assert config.db.database == "merlin"
