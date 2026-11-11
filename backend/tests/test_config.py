from pathlib import Path

import pytest

from cogplat.config import load_settings, resolve_data_dir


def test_explicit_data_directory_override_wins(tmp_path):
    override = tmp_path / "custom-data"
    result = resolve_data_dir(
        {"COGPLAT_DATA_DIR": str(override), "APPDATA": str(tmp_path / "appdata")},
        home=tmp_path,
        system="Windows",
    )
    assert result == override


def test_windows_uses_appdata(tmp_path):
    appdata = tmp_path / "Roaming"
    result = resolve_data_dir(
        {"APPDATA": str(appdata)}, home=tmp_path, system="Windows"
    )
    assert result == appdata / "CognitivePlatform"


def test_windows_fallback_uses_roaming_profile(tmp_path):
    result = resolve_data_dir({}, home=tmp_path, system="Windows")
    assert result == tmp_path / "AppData" / "Roaming" / "CognitivePlatform"


def test_macos_uses_application_support(tmp_path):
    result = resolve_data_dir({}, home=tmp_path, system="Darwin")
    assert result == tmp_path / "Library" / "Application Support" / "CognitivePlatform"


def test_linux_honors_xdg_data_home(tmp_path):
    xdg = tmp_path / "xdg"
    result = resolve_data_dir(
        {"XDG_DATA_HOME": str(xdg)}, home=tmp_path, system="Linux"
    )
    assert result == xdg / "CognitivePlatform"


def test_missing_api_token_fails_closed():
    with pytest.raises(RuntimeError, match="COGPLAT_API_TOKEN"):
        load_settings({})


def test_settings_load_token_and_data_directory(tmp_path):
    settings = load_settings(
        {
            "COGPLAT_API_TOKEN": "a-test-token",
            "COGPLAT_DATA_DIR": str(tmp_path / "data"),
        }
    )
    assert settings.api_token == "a-test-token"
    assert settings.data_dir == tmp_path / "data"
