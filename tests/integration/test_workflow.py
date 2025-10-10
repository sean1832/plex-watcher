"""Integration test example for full workflow"""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from plex_watcher.core.plex_watcher_service import PlexWatcherService


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete workflows"""

    @pytest.mark.slow
    def test_watch_and_scan_workflow(self, mock_plex_with_sections, temp_dir):
        """Test complete workflow: configure, add paths, start, scan."""
        # This is a placeholder for real integration tests
        # In a real scenario, you'd use a test Plex server or more sophisticated mocks

        service = PlexWatcherService()
        test_path = temp_dir / "media"
        test_path.mkdir()

        with patch(
            "plex_watcher.core.plex_watcher_service.PlexServer",
            return_value=mock_plex_with_sections,
        ):
            with patch("plex_watcher.core.plex_watcher_service.PlexScanner"):
                with patch("plex_watcher.core.plex_watcher_service.PlexWatcherHandler"):
                    # Configure service
                    service.configure("http://localhost:32400", "test_token", 30)

                    # Add paths
                    service.add_path(str(test_path))

                    # Start watching
                    service.start()
                    assert service.is_watching is True

                    # Simulate some activity
                    time.sleep(0.5)

                    # Stop watching
                    service.stop()
                    assert service.is_watching is False
