import pytest

from plc.models import OpcUaConfig
from plc.tag_map import TagMap, TagMapError, load_config


def test_load_example_config_resolves_y_actual_pos():
    config = load_config("config/opcua.example.json")
    tag_map = TagMap(config)
    assert tag_map.resolve("y_actual_pos") == "ns=4;s=|var|MAT LC-C07.Application.GVL.ActualY_mm"


def test_missing_tag_raises():
    config = load_config("config/opcua.example.json")
    tag_map = TagMap(config)
    with pytest.raises(TagMapError):
        tag_map.resolve("does_not_exist")


def test_no_endpoint_means_demo_mode():
    # NOT config/opcua.json: that file is the live, locally-customized
    # deployment config (may legitimately hold a real PLC endpoint), so a
    # test must not depend on its current endpoint value.
    assert OpcUaConfig(endpoint="").is_configured is False


def test_endpoint_present_means_configured():
    assert OpcUaConfig(endpoint="opc.tcp://192.168.0.2:4840").is_configured is True


def test_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(TagMapError):
        load_config(missing)


def test_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(TagMapError):
        load_config(bad)


def test_save_config_creates_missing_parent_directory(tmp_path):
    """Taşınabilir/paketli bir dağıtımda `config/` klasörü ilk çalıştırmada
    hiç yoksa (config eksik -> Demo moda düşüldü), Ayarlar'dan "Kaydet"
    burada olmadan FileNotFoundError verirdi."""
    from plc.tag_map import save_config

    target = tmp_path / "fresh_config_dir" / "opcua.json"
    assert not target.parent.exists()

    save_config(OpcUaConfig(endpoint="opc.tcp://192.168.0.2:4840"), target)

    assert target.exists()
    assert "192.168.0.2" in target.read_text(encoding="utf-8")
