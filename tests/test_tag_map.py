import pytest

from plc.tag_map import TagMap, TagMapError, load_config


def test_load_example_config_resolves_ipc_y_pos():
    config = load_config("config/opcua.example.json")
    tag_map = TagMap(config)
    assert tag_map.resolve("ipc_y_pos") == "ns=4;s=|var|MAT LC-C07.Application.GVL.IPC_Y_POS"


def test_missing_tag_raises():
    config = load_config("config/opcua.example.json")
    tag_map = TagMap(config)
    with pytest.raises(TagMapError):
        tag_map.resolve("does_not_exist")


def test_no_endpoint_means_demo_mode():
    config = load_config("config/opcua.json")
    assert config.is_configured is False


def test_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(TagMapError):
        load_config(missing)


def test_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(TagMapError):
        load_config(bad)
