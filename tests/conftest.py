"""Pytest configuration and shared fixtures"""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest
from plexapi.library import LibrarySection
from plexapi.server import PlexServer


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_plex_server() -> Mock:
    """Create a mock Plex server."""
    server = Mock(spec=PlexServer)
    server._baseurl = "http://localhost:32400"
    server._token = "test_token"

    # Mock library
    mock_library = Mock()
    server.library = mock_library

    return server


@pytest.fixture
def mock_movie_section() -> Mock:
    """Create a mock movie library section."""
    section = Mock(spec=LibrarySection)
    section.title = "Movies"
    section.type = "movie"
    section.key = "1"
    section.locations = ["/media/movies"]
    section.update = Mock()
    return section


@pytest.fixture
def mock_show_section() -> Mock:
    """Create a mock TV show library section."""
    section = Mock(spec=LibrarySection)
    section.title = "TV Shows"
    section.type = "show"
    section.key = "2"
    section.locations = ["/media/tv"]
    section.update = Mock()
    return section


@pytest.fixture
def mock_plex_with_sections(mock_plex_server, mock_movie_section, mock_show_section) -> Mock:
    """Create a mock Plex server with movie and TV sections."""
    mock_plex_server.library.sections.return_value = [mock_movie_section, mock_show_section]
    return mock_plex_server


@pytest.fixture
def sample_movie_structure(temp_dir: Path) -> Path:
    """
    Create a sample movie directory structure:
    /temp_dir/
        movies/
            Inception/
                Inception.mkv
            The Matrix/
                The.Matrix.1999.mkv
    """
    movies_dir = temp_dir / "movies"
    movies_dir.mkdir()

    # Create Inception movie
    inception_dir = movies_dir / "Inception"
    inception_dir.mkdir()
    (inception_dir / "Inception.mkv").write_text("fake video content")

    # Create Matrix movie
    matrix_dir = movies_dir / "The Matrix"
    matrix_dir.mkdir()
    (matrix_dir / "The.Matrix.1999.mkv").write_text("fake video content")

    return movies_dir


@pytest.fixture
def sample_tv_structure(temp_dir: Path) -> Path:
    """
    Create a sample TV show directory structure:
    /temp_dir/
        tv/
            Breaking Bad/
                Season 1/
                    S01E01.mkv
                    S01E02.mkv
                Season 2/
                    S02E01.mkv
    """
    tv_dir = temp_dir / "tv"
    tv_dir.mkdir()

    # Create Breaking Bad show
    show_dir = tv_dir / "Breaking Bad"
    show_dir.mkdir()

    season1_dir = show_dir / "Season 1"
    season1_dir.mkdir()
    (season1_dir / "S01E01.mkv").write_text("fake video content")
    (season1_dir / "S01E02.mkv").write_text("fake video content")

    season2_dir = show_dir / "Season 2"
    season2_dir.mkdir()
    (season2_dir / "S02E01.mkv").write_text("fake video content")

    return tv_dir


@pytest.fixture
def mock_roots(sample_movie_structure: Path, sample_tv_structure: Path) -> list:
    """Create mock Plex roots for testing."""
    movie_section = Mock(spec=LibrarySection)
    movie_section.title = "Movies"
    movie_section.type = "movie"
    movie_section.key = "1"
    movie_section.update = Mock()

    tv_section = Mock(spec=LibrarySection)
    tv_section.title = "TV Shows"
    tv_section.type = "show"
    tv_section.key = "2"
    tv_section.update = Mock()

    return [
        (sample_tv_structure, tv_section),
        (sample_movie_structure, movie_section),
    ]
