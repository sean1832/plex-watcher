"""Unit tests for API Server"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api_server import router
from backend.core.plex_watcher_service import PlexWatcherService


class TestAPIServer:
    """Test suite for FastAPI server endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Create a mock PlexWatcherService."""
        service = Mock(spec=PlexWatcherService)
        service.get_status.return_value = {
            "is_watching": False,
            "paths": [],
            "server": None,
            "cooldown": 30,
        }
        service.is_watching = False
        return service

    @pytest.fixture
    def client(self, mock_service):
        """Create a test client."""
        app = router(mock_service)
        return TestClient(app)

    def test_root_redirects_to_status(self, client):
        """Test root endpoint redirects to /status."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/status" in response.headers["location"]

    def test_get_status(self, client, mock_service):
        """Test GET /status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "is_watching" in data
        assert "paths" in data
        assert "server" in data
        assert "cooldown" in data

        mock_service.get_status.assert_called_once()

    def test_start_watcher_success(self, client, mock_service):
        """Test POST /start endpoint with valid configuration."""
        mock_service.update_configuration = Mock()
        mock_service.start = Mock()
        mock_service.is_watching = False

        response = client.post(
            "/start",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": ["/movies", "/tv"],
                "cooldown": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "started successfully" in data["message"].lower()

        mock_service.update_configuration.assert_called_once_with(
            server_url="http://localhost:32400",
            token="test_token",
            paths=["/movies", "/tv"],
            cooldown=60,
        )
        mock_service.start.assert_called_once()

    def test_start_watcher_with_default_cooldown(self, client, mock_service):
        """Test POST /start endpoint with default cooldown value."""
        mock_service.update_configuration = Mock()
        mock_service.start = Mock()
        mock_service.is_watching = False

        response = client.post(
            "/start",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": ["/movies"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Should use default cooldown of 30
        mock_service.update_configuration.assert_called_once()
        call_args = mock_service.update_configuration.call_args
        assert call_args.kwargs["cooldown"] == 30

    def test_start_watcher_stops_existing_watcher(self, client, mock_service):
        """Test POST /start stops existing watcher before reconfiguring."""
        mock_service.update_configuration = Mock()
        mock_service.start = Mock()
        mock_service.stop = Mock()
        mock_service.is_watching = True  # Watcher is already running

        response = client.post(
            "/start",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": ["/movies"],
                "cooldown": 45,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Should stop first
        mock_service.stop.assert_called_once()
        mock_service.update_configuration.assert_called_once()
        mock_service.start.assert_called_once()

    def test_start_watcher_path_not_found(self, client, mock_service):
        """Test POST /start endpoint with non-existent path."""
        mock_service.update_configuration.side_effect = FileNotFoundError(
            "Path '/nonexistent' does not exist."
        )
        mock_service.is_watching = False

        response = client.post(
            "/start",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": ["/nonexistent"],
                "cooldown": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "does not exist" in data["message"]

    def test_start_watcher_configuration_error(self, client, mock_service):
        """Test POST /start endpoint with configuration error."""
        mock_service.update_configuration.side_effect = Exception("Connection failed")
        mock_service.is_watching = False

        response = client.post(
            "/start",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": ["/movies"],
                "cooldown": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Connection failed" in data["message"]

    def test_stop_watching_success(self, client, mock_service):
        """Test POST /stop endpoint."""
        mock_service.stop = Mock()

        response = client.post("/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        mock_service.stop.assert_called_once()

    def test_stop_watching_error(self, client, mock_service):
        """Test POST /stop endpoint with error."""
        mock_service.stop.side_effect = Exception("Stop failed")

        response = client.post("/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Stop failed" in data["message"]

    def test_scan_directories_success(self, client):
        """Test POST /scan endpoint with valid paths."""
        with patch.object(PlexWatcherService, 'scan_paths') as mock_scan:
            response = client.post(
                "/scan",
                json={
                    "server_url": "http://localhost:32400",
                    "token": "test_token",
                    "paths": ["/path/to/scan1", "/path/to/scan2"]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            assert mock_scan.call_count == 2

    def test_scan_directories_empty_list(self, client):
        """Test POST /scan endpoint with empty path list."""
        response = client.post(
            "/scan",
            json={
                "server_url": "http://localhost:32400",
                "token": "test_token",
                "paths": []
            }
        )

        assert response.status_code == 400
        assert "Path parameter is required" in response.json()["detail"]

    def test_scan_directories_file_not_found(self, client):
        """Test POST /scan endpoint with non-existent path."""
        with patch.object(PlexWatcherService, 'scan_paths') as mock_scan:
            mock_scan.side_effect = FileNotFoundError("Path not found")

            response = client.post(
                "/scan",
                json={
                    "server_url": "http://localhost:32400",
                    "token": "test_token",
                    "paths": ["/nonexistent/path"]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Path not found" in data["details"][0]

    def test_scan_directories_partial_errors(self, client):
        """Test POST /scan with some paths failing."""
        with patch.object(PlexWatcherService, 'scan_paths') as mock_scan:
            def scan_side_effect(paths, server_url, token):
                if paths and "bad" in paths[0]:
                    raise Exception(f"Error scanning '{paths[0]}'")

            mock_scan.side_effect = scan_side_effect

            response = client.post(
                "/scan",
                json={
                    "server_url": "http://localhost:32400",
                    "token": "test_token",
                    "paths": ["/good/path", "/bad/path", "/another/good/path"]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert len(data["details"]) == 1
