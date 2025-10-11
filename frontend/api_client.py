"""Async API client for communicating with the Plex Watcher backend."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from frontend.config import config
from frontend.models import ApiResponse, BackendStatus

logger = logging.getLogger(__name__)


class ApiClient:
    """Async HTTP client for Plex Watcher backend API."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for the API endpoint. Defaults to config.API_ENDPOINT
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.API_ENDPOINT
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Simple cache for status to reduce backend load
        self._status_cache: Optional[BackendStatus] = None
        self._status_cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=2)  # Cache status for 2 seconds

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client, recreating if event loop changed."""
        current_loop = asyncio.get_event_loop()

        # If loop changed or client doesn't exist, create a new client
        if self._client is None or self._loop != current_loop:
            # Close old client if it exists
            if self._client is not None:
                try:
                    await self._client.aclose()
                except Exception:
                    pass  # Ignore errors closing old client

            # Create new client for current loop
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
            self._loop = current_loop

        return self._client

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass  # Ignore errors during cleanup
            self._client = None
            self._loop = None

    async def test_connection(self, endpoint: str) -> tuple[bool, str]:
        """
        Test connection to a backend endpoint.

        Args:
            endpoint: Backend API endpoint URL to test

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create a temporary client for testing
            temp_client = httpx.AsyncClient(
                base_url=endpoint,
                timeout=3.0,
                follow_redirects=True,
            )

            try:
                response = await temp_client.get("/status")
                response.raise_for_status()

                # Connection successful
                await temp_client.aclose()
                return True, f"✅ Connected successfully to {endpoint}"

            except httpx.ConnectError:
                await temp_client.aclose()
                return False, f"❌ Cannot connect to {endpoint}. Is the backend running?"
            except httpx.TimeoutException:
                await temp_client.aclose()
                return False, f"⏱️ Connection timeout to {endpoint}"
            except httpx.HTTPError as e:
                await temp_client.aclose()
                return False, f"❌ HTTP error: {str(e)}"
            except Exception as e:
                await temp_client.aclose()
                return False, f"❌ Error: {str(e)}"

        except Exception as e:
            return False, f"❌ Failed to create connection: {str(e)}"

    def update_endpoint(self, new_endpoint: str):
        """
        Update the API endpoint and reset client.

        Args:
            new_endpoint: New backend API endpoint URL
        """
        self.base_url = new_endpoint
        # Force client recreation on next request
        if self._client:
            try:
                # We can't await here, so just set to None
                # The client will be recreated on next use
                self._client = None
                self._loop = None
            except Exception:
                pass
        # Invalidate cache when endpoint changes
        self.invalidate_cache()

    async def get_status(self, use_cache: bool = True) -> BackendStatus:
        """
        Get the current status from the backend.

        Args:
            use_cache: Whether to use cached status if available

        Returns:
            BackendStatus object containing current state
        """
        # Check cache first
        if use_cache and self._status_cache and self._status_cache_time:
            if datetime.now() - self._status_cache_time < self._cache_duration:
                return self._status_cache

        try:
            client = await self._get_client()
            response = await client.get("/status")
            response.raise_for_status()

            status = BackendStatus.from_api_response(response.json())

            # Update cache
            self._status_cache = status
            self._status_cache_time = datetime.now()

            return status

        except httpx.ConnectError:
            logger.warning(f"Unable to connect to backend API at {self.base_url}")
            return BackendStatus.disconnected()
        except httpx.TimeoutException:
            logger.warning("Request to backend API timed out")
            return BackendStatus.disconnected()
        except Exception as e:
            logger.error(f"Error fetching status: {e}")
            return BackendStatus.disconnected()

    def invalidate_cache(self):
        """Invalidate the status cache to force a fresh fetch."""
        self._status_cache = None
        self._status_cache_time = None

    async def start_watching(self, server_url: str, token: str, interval: int) -> ApiResponse:
        """
        Start watching directories.

        Args:
            server_url: Plex server URL
            token: Plex authentication token
            interval: Polling interval in seconds

        Returns:
            ApiResponse with operation result
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/start",
                params={
                    "server_url": server_url,
                    "token": token,
                    "interval": interval,
                },
            )
            response.raise_for_status()
            self.invalidate_cache()  # Invalidate cache after state change
            return ApiResponse.from_dict(response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error starting watcher: {e}")
            return ApiResponse(status="error", message=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error starting watcher: {e}")
            return ApiResponse(status="error", message=str(e))

    async def stop_watching(self) -> ApiResponse:
        """
        Stop watching directories.

        Returns:
            ApiResponse with operation result
        """
        try:
            client = await self._get_client()
            response = await client.post("/stop")
            response.raise_for_status()
            self.invalidate_cache()  # Invalidate cache after state change
            return ApiResponse.from_dict(response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error stopping watcher: {e}")
            return ApiResponse(status="error", message=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error stopping watcher: {e}")
            return ApiResponse(status="error", message=str(e))

    async def add_path(self, path: str) -> ApiResponse:
        """
        Add a path to watch.

        Args:
            path: Directory path to add

        Returns:
            ApiResponse with operation result
        """
        try:
            client = await self._get_client()
            response = await client.post("/add_path", params={"path": path})
            response.raise_for_status()
            self.invalidate_cache()  # Invalidate cache after state change
            return ApiResponse.from_dict(response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error adding path: {e}")
            return ApiResponse(status="error", message=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error adding path: {e}")
            return ApiResponse(status="error", message=str(e))

    async def remove_path(self, path: str) -> ApiResponse:
        """
        Remove a path from watch list.

        Args:
            path: Directory path to remove

        Returns:
            ApiResponse with operation result
        """
        try:
            client = await self._get_client()
            response = await client.post("/remove_path", params={"path": path})
            response.raise_for_status()
            self.invalidate_cache()  # Invalidate cache after state change
            return ApiResponse.from_dict(response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error removing path: {e}")
            return ApiResponse(status="error", message=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error removing path: {e}")
            return ApiResponse(status="error", message=str(e))

    async def scan_paths(self, paths: list[str]) -> ApiResponse:
        """
        Scan specific directories.

        Args:
            paths: List of directory paths to scan

        Returns:
            ApiResponse with operation result
        """
        try:
            client = await self._get_client()
            response = await client.post("/scan", json={"paths": paths})
            response.raise_for_status()
            return ApiResponse.from_dict(response.json())

        except httpx.HTTPError as e:
            logger.error(f"HTTP error scanning paths: {e}")
            return ApiResponse(status="error", message=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning paths: {e}")
            return ApiResponse(status="error", message=str(e))


# Singleton instance
_api_client: Optional[ApiClient] = None


def get_api_client() -> ApiClient:
    """Get or create the singleton API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = ApiClient()
    return _api_client


def run_async(coro):
    """
    Run an async coroutine in a synchronous context.

    This is a helper for Streamlit which is synchronous.
    Properly handles event loop management across Streamlit reruns.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, try to get the event loop for this thread
        try:
            loop = asyncio.get_event_loop()
            # Check if loop is closed (can happen after Streamlit rerun)
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
