"""Unit tests for PlexScanner class"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.core.plex_path import PlexPath
from backend.core.plex_scanner import PlexScanner


class TestPlexScanner:
    """Test suite for PlexScanner functionality"""

    def test_initialization(self, mock_plex_with_sections):
        """Test PlexScanner initialization with sections."""
        scanner = PlexScanner(mock_plex_with_sections)

        assert scanner.plex == mock_plex_with_sections
        assert len(scanner.sections) == 2
        assert "Movies" in scanner.sections
        assert "TV Shows" in scanner.sections
        assert len(scanner._roots) == 2

    def test_roots_sorted_by_length(self, mock_plex_with_sections):
        """Test that roots are sorted by path length (longest first)."""
        scanner = PlexScanner(mock_plex_with_sections)

        # Should be sorted longest path first
        if len(scanner._roots) >= 2:
            first_len = len(str(scanner._roots[0][0]))
            second_len = len(str(scanner._roots[1][0]))
            assert first_len >= second_len

    def test_get_type_movie(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test getting type for a movie path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_file = sample_movie_structure / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, movie_file)

        media_type = scanner.get_type(plex_path)
        assert media_type == "movie"

    def test_get_type_show(self, mock_plex_with_sections, mock_roots, sample_tv_structure):
        """Test getting type for a TV show path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        tv_file = sample_tv_structure / "Breaking Bad" / "Season 1" / "S01E01.mkv"
        plex_path = PlexPath(mock_roots, tv_file)

        media_type = scanner.get_type(plex_path)
        assert media_type == "show"

    def test_get_type_directory(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test getting type for a directory path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        media_type = scanner.get_type(plex_path)
        assert media_type == "movie"

    def test_scan_section(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test scanning a Plex section."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        with patch("time.sleep"):  # Mock sleep to speed up test
            scanner.scan_section(plex_path)

        # Verify that the section's update method was called
        movie_section = mock_roots[1][1]  # Get movie section from roots
        movie_section.update.assert_called_once()

    def test_find_section(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test finding the correct section for a path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        section = scanner._find_section(plex_path)
        assert section.title == "Movies"
        assert section.type == "movie"

    def test_find_section_not_found(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test that finding section for invalid path raises ValueError."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a path outside of any Plex root
        invalid_path = temp_dir / "invalid"
        invalid_path.mkdir()
        plex_path = PlexPath(mock_roots, invalid_path, validate=False)

        with pytest.raises(ValueError, match="No Plex section found"):
            scanner._find_section(plex_path)

    def test_find_section_id(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test finding section ID for a path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        section_id = scanner._find_section_id(plex_path)
        assert section_id == 1

    def test_scan_with_cooldown(self, mock_plex_with_sections, mock_roots, sample_movie_structure):
        """Test that scan respects cooldown parameter."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        movie_dir = sample_movie_structure / "Inception"
        plex_path = PlexPath(mock_roots, movie_dir)

        with patch("time.sleep") as mock_sleep:
            scanner.scan_section(plex_path, cooldown=2.0)
            mock_sleep.assert_called_once_with(2.0)


class TestPlexScannerEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_sections(self):
        """Test scanner with no sections."""
        mock_server = Mock()
        mock_server.library.sections.return_value = []

        scanner = PlexScanner(mock_server)
        assert len(scanner.sections) == 0
        assert len(scanner._roots) == 0

    def test_section_with_multiple_locations(self):
        """Test handling section with multiple location paths."""
        mock_server = Mock()
        mock_section = Mock()
        mock_section.title = "Multi-Location"
        mock_section.type = "movie"
        mock_section.locations = ["/media/movies1", "/media/movies2"]

        mock_server.library.sections.return_value = [mock_section]

        scanner = PlexScanner(mock_server)
        # Should create two roots, one for each location
        assert len(scanner._roots) >= 2


class TestPlexScannerDeletedPaths:
    """Test scanner handling of deleted files and directories"""

    def test_get_type_deleted_movie_file(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test getting type for a deleted movie file using path structure."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a path that looks like a movie (no "Season X" in path)
        deleted_movie = temp_dir / "movies" / "Inception" / "Inception.mkv"
        plex_path = PlexPath(mock_roots, deleted_movie, validate=False)

        # Should still be able to determine it's a movie even if deleted
        media_type = scanner.get_type(plex_path, deleted=True)
        assert media_type == "movie"

    def test_get_type_deleted_show_file(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test getting type for a deleted show file with Season folder."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a path that looks like a show (has "Season X" in path)
        deleted_show = temp_dir / "tv" / "Breaking Bad" / "Season 1" / "S01E01.mkv"
        plex_path = PlexPath(mock_roots, deleted_show, validate=False)

        # Should detect it's a show from the "Season 1" folder
        media_type = scanner.get_type(plex_path, deleted=True)
        assert media_type == "show"

    def test_get_type_deleted_directory(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test getting type for a deleted directory."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a path for a deleted movie directory
        deleted_dir = temp_dir / "movies" / "Inception"
        plex_path = PlexPath(mock_roots, deleted_dir, validate=False)

        # Should still work for deleted directories
        media_type = scanner.get_type(plex_path, deleted=True)
        assert media_type == "movie"

    def test_get_type_deleted_show_directory(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test getting type for a deleted show directory with Season in path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a path with Season folder
        deleted_dir = temp_dir / "tv" / "Breaking Bad" / "Season 2"
        plex_path = PlexPath(mock_roots, deleted_dir, validate=False)

        # Should detect show type from Season folder
        media_type = scanner.get_type(plex_path, deleted=True)
        assert media_type == "show"

    def test_find_section_deleted_path(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test finding section for a deleted path."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a deleted path under movies root
        deleted_path = temp_dir / "movies" / "SomeMovie" / "file.mkv"
        plex_path = PlexPath(mock_roots, deleted_path, validate=False)

        # Should still find the section by path matching
        section = scanner._find_section(plex_path, allow_deleted=True)
        assert section.title == "Movies"

    def test_scan_section_deleted_path(self, mock_plex_with_sections, mock_roots, temp_dir):
        """Test that scanning a deleted path still triggers Plex update."""
        scanner = PlexScanner(mock_plex_with_sections)
        scanner._roots = mock_roots

        # Create a deleted path
        deleted_path = temp_dir / "movies" / "DeletedMovie"
        plex_path = PlexPath(mock_roots, deleted_path, validate=False)

        with patch("time.sleep"):
            scanner.scan_section(plex_path)

        # Verify that the section's update method was called
        movie_section = mock_roots[1][1]
        movie_section.update.assert_called_once()

