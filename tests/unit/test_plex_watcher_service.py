"""Unit tests for PlexWatcherService class"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.core.plex_watcher_service import PlexWatcherService


class TestPlexWatcherService:
    """Test suite for PlexWatcherService functionality"""

    def test_initialization(self):
        """Test service initialization."""
        service = PlexWatcherService()

        assert service.observer is not None
        assert len(service.paths) == 0
        assert service.server is None
        assert service.handler is None
        assert service.scanner is None
        assert service.cooldown == 30
        assert service.is_watching is False

    def test_get_status_not_configured(self):
        """Test get_status when service is not configured."""
        service = PlexWatcherService()
        status = service.get_status()

        assert status["is_watching"] is False
        assert status["paths"] == []
        assert status["server"] is None
        assert status["cooldown"] == 30

    def test_configure(self, mock_plex_server):
        """Test configuring the service."""
        service = PlexWatcherService()

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 60)

        assert service.server is not None
        assert service.cooldown == 60
        assert service.scanner is not None
        assert service.handler is not None

    def test_update_configuration_valid(self, mock_plex_server, temp_dir):
        """Test updating configuration with valid paths."""
        service = PlexWatcherService()
        test_path1 = temp_dir / "movies"
        test_path2 = temp_dir / "tv"
        test_path1.mkdir()
        test_path2.mkdir()

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.update_configuration(
                        server_url="http://localhost:32400",
                        token="test_token",
                        paths=[str(test_path1), str(test_path2)],
                        cooldown=45,
                    )

        assert service.server is not None
        assert service.cooldown == 45
        assert service.scanner is not None
        assert service.handler is not None
        assert len(service.paths) == 2

    def test_update_configuration_replaces_paths(self, mock_plex_server, temp_dir):
        """Test that update_configuration replaces existing paths."""
        service = PlexWatcherService()
        old_path = temp_dir / "old"
        new_path = temp_dir / "new"
        old_path.mkdir()
        new_path.mkdir()

        # Add initial path
        service.add_path(str(old_path))
        assert len(service.paths) == 1

        # Update configuration with new path
        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.update_configuration(
                        server_url="http://localhost:32400",
                        token="test_token",
                        paths=[str(new_path)],
                        cooldown=30,
                    )

        # Old path should be gone, only new path remains
        assert len(service.paths) == 1
        assert new_path in service.paths
        assert old_path not in service.paths

    def test_update_configuration_invalid_path(self, mock_plex_server):
        """Test update_configuration with non-existent path fails fast."""
        service = PlexWatcherService()

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with pytest.raises(FileNotFoundError):
                service.update_configuration(
                    server_url="http://localhost:32400",
                    token="test_token",
                    paths=["/nonexistent/path"],
                    cooldown=30,
                )

        # Service should not be partially configured
        assert service.scanner is None
        assert len(service.paths) == 0

    def test_update_configuration_partial_invalid_paths(self, mock_plex_server, temp_dir):
        """Test update_configuration with some invalid paths fails atomically."""
        service = PlexWatcherService()
        valid_path = temp_dir / "valid"
        valid_path.mkdir()

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with pytest.raises(FileNotFoundError):
                service.update_configuration(
                    server_url="http://localhost:32400",
                    token="test_token",
                    paths=[str(valid_path), "/nonexistent/path"],
                    cooldown=30,
                )

        # No paths should be added due to atomic validation
        assert len(service.paths) == 0

    def test_add_path_valid(self, temp_dir):
        """Test adding a valid path."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()

        service.add_path(str(test_path))

        assert len(service.paths) == 1
        assert test_path in service.paths

    def test_add_path_invalid(self):
        """Test adding a non-existent path raises FileNotFoundError."""
        service = PlexWatcherService()

        with pytest.raises(FileNotFoundError):
            service.add_path("/nonexistent/path")

    def test_add_path_resolves(self, temp_dir):
        """Test that added paths are resolved to absolute paths."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()

        # Add path with relative components
        service.add_path(str(test_path))

        # Path should be resolved
        added_path = list(service.paths)[0]
        assert added_path.is_absolute()

    def test_start_not_configured(self, temp_dir):
        """Test starting service without configuration raises RuntimeError."""
        service = PlexWatcherService()
        # Create a test path in temp_dir
        test_path = temp_dir / "media"
        test_path.mkdir()
        service.add_path(str(test_path))

        with pytest.raises(RuntimeError, match="not configured"):
            service.start()

    def test_start_configured(self, mock_plex_server, temp_dir):
        """Test starting a properly configured service."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()
        service.add_path(str(test_path))

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        service.start()

        assert service.is_watching is True
        assert service.observer.is_alive()

    def test_start_already_watching(self, mock_plex_server, temp_dir):
        """Test starting service when already watching."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()
        service.add_path(str(test_path))

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        service.start()
        assert service.is_watching is True

        # Starting again should be a no-op
        service.start()
        assert service.is_watching is True

    def test_stop_when_watching(self, mock_plex_server, temp_dir):
        """Test stopping a running service."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()
        service.add_path(str(test_path))

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        service.start()
        service.stop()

        assert service.is_watching is False

    def test_stop_when_not_watching(self):
        """Test stopping service when not watching."""
        service = PlexWatcherService()

        # Should be a no-op, not raise an error
        service.stop()
        assert service.is_watching is False

    def test_restart(self, mock_plex_server, temp_dir):
        """Test restarting the service."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()
        service.add_path(str(test_path))

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        service.start()
        service.restart()

        assert service.is_watching is True

    def test_scan_path_not_configured(self):
        """Test scanning path without proper parameters."""
        # The scan_paths is a static method that requires server_url and token
        # Testing with invalid/empty server_url should fail
        with pytest.raises(Exception):  # Will fail when trying to connect to PlexServer
            PlexWatcherService.scan_paths(
                paths=["."],
                server_url="",
                token=""
            )

    def test_scan_path_invalid(self, mock_plex_server):
        """Test scanning non-existent path raises FileNotFoundError."""
        # Mock PlexScanner to avoid needing full Plex setup
        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with pytest.raises(FileNotFoundError):
                    PlexWatcherService.scan_paths(
                        paths=["/nonexistent/path"],
                        server_url="http://localhost:32400",
                        token="test_token"
                    )

    def test_scan_path_valid(self, mock_plex_server, temp_dir, mock_roots):
        """Test scanning a valid path."""
        test_path = temp_dir / "test"
        test_path.mkdir()

        mock_scanner = Mock()
        mock_scanner._roots = mock_roots

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner", return_value=mock_scanner):
                with patch("backend.core.plex_watcher_service.PlexPath"):
                    PlexWatcherService.scan_paths(
                        paths=[str(test_path)],
                        server_url="http://localhost:32400",
                        token="test_token"
                    )
                    mock_scanner.scan_section.assert_called_once()


class TestPlexWatcherServiceBugs:
    """Test cases that expose known bugs"""

    def test_restart_after_stop_bug(self, mock_plex_server, temp_dir):
        """Test that observer can be restarted after stop() (bug is now fixed)."""
        service = PlexWatcherService()
        test_path = temp_dir / "test"
        test_path.mkdir()
        service.add_path(str(test_path))

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        service.start()
        service.stop()

        # This should now work because observer is recreated in stop()
        service.start()
        assert service.is_watching is True
        service.stop()

    def test_start_without_paths(self, mock_plex_server):
        """Test starting service with no paths to watch raises error."""
        service = PlexWatcherService()

        with patch("backend.core.plex_watcher_service.PlexServer", return_value=mock_plex_server):
            with patch("backend.core.plex_watcher_service.PlexScanner"):
                with patch("backend.core.plex_watcher_service.PlexWatcherHandler"):
                    service.configure("http://localhost:32400", "test_token", 30)

        # This should now raise an error since we added validation
        with pytest.raises(RuntimeError, match="No paths configured"):
            service.start()
