import os
from pathlib import Path
from typing import Union

from plexapi.library import LibrarySection


class PlexPath:
    """
    A wrapper for Plex library paths with validation.

    Can be created in two ways:
    - Direct construction with roots validation: PlexPath(roots, local_path)
    - From a validated path string: PlexPath.from_path(roots, path_str)
    """

    def __init__(
        self,
        roots: list[tuple[Path, LibrarySection]],
        local_path: Union[str, Path],
        validate: bool = True,
    ):
        """
        Create a PlexPath by converting a local path to its Plex equivalent.

        Args:
            roots: List of tuples containing (plex_root_path, library_section)
            local_path: The local filesystem path to convert
            validate: Whether to validate the path exists in a Plex root (default: True)

        Raises:
            ValueError: If validation is enabled and the path is not in any Plex root
        """
        if not roots:
            raise ValueError("No Plex roots provided. Cannot create PlexPath.")

        self._roots = roots
        local_path = Path(local_path).resolve()

        # Always convert to Plex path
        try:
            plex_path = self._convert_to_plex_path(local_path)
            self._path = plex_path
        except ValueError:
            if validate:
                # Re-raise if validation is required
                raise
            else:
                # If validation is disabled, just use the path as-is
                # This handles edge cases where conversion fails
                self._path = local_path

    def _convert_to_plex_path(self, local_path: Path) -> Path:
        """
        Convert a local filesystem path to its Plex library equivalent.

        Args:
            local_path: The local path to convert

        Returns:
            The converted Plex path

        Raises:
            ValueError: If no matching Plex root is found
        """
        # Get parts, filtering out empty strings and separators
        parts = [p for p in local_path.parts if p and p != os.sep and p != "\\" and p != "/"]
        lower_parts = [p.lower() for p in parts]

        best_root = None
        best_k = 0
        best_children: tuple[str, ...] = ()

        for plex_root, _ in self._roots:
            # Get Plex root parts
            plex_parts = [
                p for p in plex_root.parts if p and p != os.sep and p != "\\" and p != "/"
            ]
            lower_plex = [p.lower() for p in plex_parts]
            max_k = min(len(plex_parts), len(parts))

            # try longest suffix→shortest
            for k in range(max_k, 0, -1):
                suffix = lower_plex[-k:]
                for idx in range(len(lower_parts) - k + 1):
                    if lower_parts[idx : idx + k] == suffix:
                        # now slice children from the same 'parts' list
                        children = tuple(parts[idx + k :])
                        if k > best_k:
                            best_root = plex_root
                            best_k = k
                            best_children = children
                        break
                if best_k == k:
                    break

        if best_root and best_k > 0:
            # Reconstruct the path using the plex root and children
            return Path(best_root, *best_children)
        else:
            # No match found - this is an error condition
            raise ValueError(
                f"Could not map local path '{local_path}' to any Plex library root. "
                f"Available roots: {[str(root.as_posix()) for root, _ in self._roots]}"
            )

    @classmethod
    def from_path(
        cls,
        roots: list[tuple[Path, LibrarySection]],
        path: Union[str, Path],
        validate: bool = True,
    ) -> "PlexPath":
        """
        Create a PlexPath from a path string or Path object.

        This is an alias for the constructor, provided for clarity.

        Args:
            roots: List of tuples containing (plex_root_path, library_section)
            path: The path to wrap (can be str or Path)
            validate: Whether to validate the path exists in a Plex root

        Returns:
            A PlexPath instance

        Raises:
            ValueError: If validation fails
        """
        return cls(roots, path, validate=validate)

    @property
    def path(self) -> Path:
        """Get the underlying Path object."""
        return self._path

    def __str__(self) -> str:
        """Return the path as a string."""
        return str(self._path)

    def __repr__(self) -> str:
        """Return a repr string."""
        return f"PlexPath('{self._path}')"

    def __fspath__(self) -> str:
        """Support os.fspath() protocol."""
        return str(self._path)

    # Delegate common Path methods to the underlying path
    @property
    def parent(self) -> Path:
        """Return the parent directory."""
        return self._path.parent

    @property
    def name(self) -> str:
        """Return the final component of the path."""
        return self._path.name

    def exists(self) -> bool:
        """Check if the path exists."""
        return self._path.exists()

    def is_dir(self) -> bool:
        """Check if the path is a directory."""
        return self._path.is_dir()

    def is_file(self) -> bool:
        """Check if the path is a file."""
        return self._path.is_file()
