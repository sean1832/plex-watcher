"""Unit tests for environment configuration module."""

import os
from pathlib import Path

import pytest

from backend.core.env_config import (
    EnvironmentConfig,
    get_config,
    get_env_bool,
    get_env_int,
    get_env_str,
    reload_config,
)


class TestEnvHelpers:
    """Test environment variable helper functions."""

    def test_get_env_str_with_value(self, monkeypatch):
        monkeypatch.setenv("TEST_STRING", "test_value")
        assert get_env_str("TEST_STRING") == "test_value"

    def test_get_env_str_with_default(self):
        assert get_env_str("NONEXISTENT_VAR", "default") == "default"

    def test_get_env_int_with_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "42")
        assert get_env_int("TEST_INT") == 42

    def test_get_env_int_with_default(self):
        assert get_env_int("NONEXISTENT_VAR", 100) == 100

    def test_get_env_int_with_invalid_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "not_a_number")
        assert get_env_int("TEST_INT", 100) == 100

    def test_get_env_bool_true_values(self, monkeypatch):
        for value in ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]:
            monkeypatch.setenv("TEST_BOOL", value)
            assert get_env_bool("TEST_BOOL") is True

    def test_get_env_bool_false_values(self, monkeypatch):
        for value in ["false", "FALSE", "0", "no", "off", "anything"]:
            monkeypatch.setenv("TEST_BOOL", value)
            assert get_env_bool("TEST_BOOL") is False

    def test_get_env_bool_with_default(self):
        assert get_env_bool("NONEXISTENT_VAR", True) is True
        assert get_env_bool("NONEXISTENT_VAR", False) is False


class TestEnvironmentConfig:
    """Test EnvironmentConfig class."""

    def test_default_values(self, monkeypatch):
        # Clear all relevant env vars
        for key in ["API_HOST", "API_PORT", "LOG_LEVEL", "MEDIA_ROOT", "CONFIG_PATH", "CORS_ORIGINS"]:
            monkeypatch.delenv(key, raising=False)
        
        config = EnvironmentConfig()
        
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8000
        assert config.log_level == "INFO"
        assert config.media_root == "/media"
        assert config.config_path.name == "config.json"
        assert "http://localhost:5173" in config.cors_origins

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("API_HOST", "127.0.0.1")
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MEDIA_ROOT", "/custom/media")
        monkeypatch.setenv("CONFIG_PATH", "/custom/config.json")
        monkeypatch.setenv("CORS_ORIGINS", "http://example.com,http://test.com")
        
        config = EnvironmentConfig()
        
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 9000
        assert config.log_level == "DEBUG"
        assert config.media_root == "/custom/media"
        assert str(config.config_path).endswith("config.json")
        assert config.cors_origins == ["http://example.com", "http://test.com"]

    def test_cors_origins_parsing(self, monkeypatch):
        # Test with spaces
        monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com , http://c.com")
        config = EnvironmentConfig()
        assert config.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]
        
        # Test with empty strings
        monkeypatch.setenv("CORS_ORIGINS", "http://a.com,,http://b.com")
        config = EnvironmentConfig()
        assert config.cors_origins == ["http://a.com", "http://b.com"]

    def test_repr(self, monkeypatch):
        monkeypatch.setenv("API_HOST", "localhost")
        monkeypatch.setenv("API_PORT", "3000")
        config = EnvironmentConfig()
        
        repr_str = repr(config)
        assert "api_host='localhost'" in repr_str
        assert "api_port=3000" in repr_str


class TestConfigSingleton:
    """Test global configuration instance management."""

    def test_get_config_singleton(self, monkeypatch):
        """Test that get_config returns the same instance."""
        monkeypatch.setenv("API_HOST", "test_host")
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2

    def test_reload_config(self, monkeypatch):
        """Test that reload_config creates a new instance."""
        monkeypatch.setenv("API_HOST", "original")
        config1 = get_config()
        
        monkeypatch.setenv("API_HOST", "updated")
        config2 = reload_config()
        
        assert config1 is not config2
        assert config2.api_host == "updated"
