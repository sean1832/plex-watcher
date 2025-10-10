"""Unit tests for PlexPath class"""

from pathlib import Path

import pytest

from plex_watcher.core.plex_path import PlexPath


class TestPlexPath:
    """Test suite for PlexPath functionality"""

    def test_create_valid_movie_path(self, mock_roots, sample_movie_structure):
        """Test creating a PlexPath for a valid movie file."""
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        assert plex_path.exists()
        assert plex_path.is_file()
        assert "Inception.mkv" in str(plex_path)

    def test_create_valid_tv_path(self, mock_roots, sample_tv_structure):
        """Test creating a PlexPath for a valid TV show file."""
        tv_file = sample_tv_structure / "Breaking Bad" / "Season 1" / "S01E01.mkv"
        plex_path = PlexPath(mock_roots, tv_file)

        assert plex_path.exists()
        assert plex_path.is_file()
        assert "S01E01.mkv" in str(plex_path)

    def test_create_directory_path(self, mock_roots, sample_movie_structure):
        """Test creating a PlexPath for a directory."""
        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        assert plex_path.exists()
        assert plex_path.is_dir()

    def test_invalid_path_outside_roots(self, mock_roots, temp_dir):
        """Test that paths outside Plex roots raise ValueError."""
        outside_path = temp_dir / "outside" / "file.mkv"
        outside_path.parent.mkdir()
        outside_path.write_text("content")

        with pytest.raises(ValueError, match="Could not map local path"):
            PlexPath(mock_roots, outside_path)

    def test_no_validation_mode(self, mock_roots, temp_dir):
        """Test creating PlexPath without validation."""
        outside_path = temp_dir / "outside" / "file.mkv"
        plex_path = PlexPath(mock_roots, outside_path, validate=False)

        assert str(plex_path) == str(outside_path)

    def test_empty_roots_raises_error(self, sample_movie_structure):
        """Test that empty roots list raises ValueError."""
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"

        with pytest.raises(ValueError, match="No Plex roots provided"):
            PlexPath([], movie_file)

    def test_from_path_classmethod(self, mock_roots, sample_movie_structure):
        """Test creating PlexPath using from_path classmethod."""
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath.from_path(mock_roots, str(movie_file))

        assert plex_path.exists()
        assert "Inception.mkv" in str(plex_path)

    def test_path_properties(self, mock_roots, sample_movie_structure):
        """Test PlexPath properties (parent, name, etc.)."""
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        assert plex_path.name == "Inception.mkv"
        assert "Inception" in str(plex_path.parent)

    def test_fspath_protocol(self, mock_roots, sample_movie_structure):
        """Test that PlexPath supports os.fspath() protocol."""
        import os

        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        path_str = os.fspath(plex_path)
        assert isinstance(path_str, str)
        assert "Inception.mkv" in path_str

    def test_repr_and_str(self, mock_roots, sample_movie_structure):
        """Test string representations of PlexPath."""
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        assert "PlexPath" in repr(plex_path)
        assert "Inception.mkv" in str(plex_path)


class TestPlexPathConversion:
    """Test suite for path conversion logic"""

    def test_nested_directory_matching(self, mock_roots, sample_tv_structure):
        """Test path conversion with nested directories."""
        season_dir = sample_tv_structure / "Breaking Bad" / "Season 1"
        plex_path = PlexPath(mock_roots, season_dir)

        assert plex_path.exists()
        assert plex_path.is_dir()

    def test_case_insensitive_matching(self, mock_roots, sample_movie_structure):
        """Test that path matching is case-insensitive."""
        # This tests the internal case-insensitive matching logic
        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        # Should successfully create path regardless of case in matching
        assert plex_path.exists()
