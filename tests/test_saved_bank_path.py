from pathlib import Path

import pytest

from team import config


def test_default_bank_is_local_to_the_installation_and_created_only_on_write(tmp_path, monkeypatch):
    runs = tmp_path / "installation" / "runs"
    monkeypatch.setattr(config, "RUNS", runs)
    monkeypatch.delenv("HIVE_BANK", raising=False)
    monkeypatch.chdir(tmp_path)
    assert config.saved_bank_path() == runs / "learned-skills"
    assert not runs.exists()


@pytest.mark.parametrize("setting", ["", "  ", "off", "OFF"])
def test_explicit_setting_disables_the_bank(setting, monkeypatch):
    monkeypatch.setenv("HIVE_BANK", setting)
    assert config.saved_bank_path() is None


def test_configured_bank_takes_precedence_and_preserves_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HIVE_BANK", "~/my-bank")
    assert config.saved_bank_path() == tmp_path / "my-bank"
    monkeypatch.setenv("HIVE_BANK", "work/orders/bank")
    assert config.saved_bank_path() == Path("work/orders/bank")


def test_sdk_setup_and_chat_can_share_one_location(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS", tmp_path)
    monkeypatch.delenv("HIVE_FIELDWORK_SDK", raising=False)
    assert config.fieldwork_sdk_path() == tmp_path / "fieldwork-assets" / "wasi"
    monkeypatch.setenv("HIVE_FIELDWORK_SDK", str(tmp_path / "custom"))
    assert config.fieldwork_sdk_path() == tmp_path / "custom"


def test_setup_rejects_the_wrong_archive_without_publishing_a_guest(tmp_path):
    from scripts.setup_fieldwork import install_guest

    archive = tmp_path / "sdk.zip"
    archive.write_bytes(b"not the pinned release")
    with pytest.raises(ValueError, match="SHA-256"):
        install_guest(tmp_path / "sdk", archive)
    assert list(tmp_path.iterdir()) == [archive]
