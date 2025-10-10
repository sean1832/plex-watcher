"""Unit tests for API Server"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from plex_watcher.api_server import router
from plex_watcher.core.plex_watcher_service import PlexWatcherService


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

    def test_start_watching_success(self, client, mock_service):
        """Test POST /start endpoint with valid parameters."""
        mock_service.configure = Mock()
        mock_service.start = Mock()

        response = client.post(
            "/start",
            params={"server_url": "http://localhost:32400", "token": "test_token", "interval": 60},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        mock_service.configure.assert_called_once_with("http://localhost:32400", "test_token", 60)
        mock_service.start.assert_called_once()

    def test_start_watching_error(self, client, mock_service):
        """Test POST /start endpoint with error."""
        mock_service.configure.side_effect = Exception("Connection failed")

        response = client.post(
            "/start",
            params={"server_url": "http://localhost:32400", "token": "test_token", "interval": 60},
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

    def test_scan_directories_success(self, client, mock_service):
        """Test POST /scan endpoint with valid paths."""
        mock_service.scan_path = Mock()

        response = client.post("/scan", json=["/path/to/scan1", "/path/to/scan2"])

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        assert mock_service.scan_path.call_count == 2

    def test_scan_directories_empty_list(self, client, mock_service):
        """Test POST /scan endpoint with empty path list."""
        response = client.post("/scan", json=[])

        assert response.status_code == 400
        assert "Path parameter is required" in response.json()["detail"]

    def test_scan_directories_file_not_found(self, client, mock_service):
        """Test POST /scan endpoint with non-existent path."""
        mock_service.scan_path.side_effect = FileNotFoundError("Path not found")

        response = client.post("/scan", json=["/nonexistent/path"])

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Path not found" in data["details"][0]

    def test_scan_directories_partial_errors(self, client, mock_service):
        """Test POST /scan with some paths failing."""

        def scan_side_effect(path):
            if "bad" in path:
                raise Exception(f"Error scanning '{path}'")

        mock_service.scan_path.side_effect = scan_side_effect

        response = client.post("/scan", json=["/good/path", "/bad/path", "/another/good/path"])

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert len(data["details"]) == 1


class TestAPIServerBugs:
    """Test cases that expose bugs in the API server"""

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
        return service

    @pytest.fixture
    def client(self, mock_service):
        """Create a test client."""
        app = router(mock_service)
        return TestClient(app)

    def test_no_add_path_endpoint(self, client):
        """BUG: There is no endpoint to add paths to watch."""
        # This should exist but doesn't
        response = client.post("/add_path", json={"path": "/some/path"})
        assert response.status_code == 404

    def test_start_missing_parameters(self, client):
        """Test /start endpoint without required parameters."""
        # Missing parameters should return proper error, not 422
        response = client.post("/start")
        assert response.status_code == 422  # Validation error

    def test_no_authentication(self, client):
        """BUG: API has no authentication mechanism."""
        # Currently, anyone can access these endpoints
        # TODO comment in code mentions this should be implemented
        response = client.get("/status")
        assert response.status_code == 200
        # In a secure implementation, this should require auth
