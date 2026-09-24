"""Config and data must land somewhere writable once the program is packaged.

Both folders used to be derived from `__file__`. In a checkout that is the
repository, which is writable and already contains `config/`; packaged and
installed under `Program Files` it is neither. The alarm history and the
settings store would then fail on the customer's panel while passing every
test on every development machine -- so these tests pretend to be frozen.
"""

from __future__ import annotations

import importlib

import pytest

from app import paths


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setenv("ProgramData", r"C:\ProgramData")
    monkeypatch.delenv("BUFERA_CONFIG_DIR", raising=False)
    monkeypatch.delenv("BUFERA_DATA_DIR", raising=False)


def test_frozen_config_goes_under_programdata(frozen):
    assert paths.config_dir().as_posix().endswith(
        "ProgramData/Bufera/MakineEkrani/config")


def test_frozen_data_goes_under_programdata(frozen):
    assert paths.data_dir().as_posix().endswith(
        "ProgramData/Bufera/MakineEkrani/data")


def test_a_checkout_keeps_using_the_repository_folders(monkeypatch):
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    monkeypatch.delenv("BUFERA_CONFIG_DIR", raising=False)
    assert paths.config_dir().name == "config"
    assert paths.config_dir().parent.name == "Bufera_MakineEkrani" or \
        (paths.config_dir().parent / "app").is_dir()


def test_environment_overrides_win_in_both_modes(monkeypatch, tmp_path):
    monkeypatch.setenv("BUFERA_CONFIG_DIR", str(tmp_path / "c"))
    monkeypatch.setenv("BUFERA_DATA_DIR", str(tmp_path / "d"))
    for frozen_state in (True, False):
        monkeypatch.setattr(paths, "is_frozen", lambda: frozen_state)
        assert paths.config_dir() == tmp_path / "c"
        assert paths.data_dir() == tmp_path / "d"


def test_the_db_and_the_config_follow_those_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("BUFERA_CONFIG_DIR", str(tmp_path / "c"))
    monkeypatch.setenv("BUFERA_DATA_DIR", str(tmp_path / "d"))
    db = importlib.import_module("persistence.db")
    tag_map = importlib.import_module("plc.tag_map")

    assert db.default_db_path() == tmp_path / "d" / "bufera.db"
    assert tag_map.default_config_path() == tmp_path / "c" / "opcua.json"


def test_saving_creates_the_folder_it_needs(monkeypatch, tmp_path):
    """First commissioning writes a config where no folder exists yet."""
    from plc.models import OpcUaConfig
    from plc.tag_map import load_config, save_config

    target = tmp_path / "hic" / "olmayan" / "opcua.json"
    save_config(OpcUaConfig(endpoint="opc.tcp://ornek-plc:4840"), target)

    assert target.is_file()
    assert load_config(target).endpoint == "opc.tcp://ornek-plc:4840"
