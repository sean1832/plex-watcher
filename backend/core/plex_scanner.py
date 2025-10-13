import time
from pathlib import Path
from typing import Literal

from plexapi.library import LibrarySection
from plexapi.server import PlexServer

from backend import logger
from backend.core.plex_path import PlexPath


class PlexScanner:
    def __init__(self, plex: PlexServer):
        self.plex = plex

        # 1) fetch all sections
        self.sections = {sec.title: sec for sec in plex.library.sections()}
        # 2) build list of (plex_root_path, section)
        mapping = []
        for sec in self.sections.values():
            for loc in sec.locations:
                plex_root = Path(loc)
                mapping.append((plex_root, sec))
        # sort longest paths first (nested libs before top‐level)
        self._roots: list[tuple[Path, LibrarySection]] = sorted(
            mapping, key=lambda rs: len(str(rs[0])), reverse=True
        )

        for root, sec in self._roots:
            logger.info(f"Found Plex section: '{sec.title}' at {root}")

    def get_type(self, path: PlexPath, deleted: bool = False) -> Literal["movie", "show"]:
        """
        Figure out whether a given file/folder belongs to Movies or TV library,
        and return "movie" for a Movies section, or "show" for a TV Shows section.
        
        Args:
            path: The PlexPath to check
            deleted: If True, the path is deleted and filesystem checks should be avoided
        """
        # For deleted paths, use heuristics since we can't check the filesystem
        if deleted:
            # Try to determine from path structure
            # Shows typically have "Season X" folders in their path
            path_str = str(path.path).lower()
            parts = path.path.parts
            
            # Check if any part contains "season" followed by a number
            for part in parts:
                part_lower = part.lower()
                if part_lower.startswith("season") and any(c.isdigit() for c in part_lower):
                    # This looks like a TV show structure
                    section = self._find_section(path, allow_deleted=True)
                    if section and section.type.lower() == "show":
                        return "show"
                    # If section says it's a show, trust that
                    # Otherwise fall through to section check
                    break
            
            # Fall back to section detection (this should work even for deleted paths)
            section = self._find_section(path, allow_deleted=True)
            lib_type = section.type.lower()
            if lib_type == "movie":
                return "movie"
            elif lib_type == "show":
                return "show"
            else:
                return "movie"
        
        # For existing paths, use filesystem checks
        if path.exists() and path.is_dir():
            dir_path = path
        else:
            # If it's a file, create PlexPath for its parent
            dir_path = PlexPath(self._roots, path.parent, validate=False)

        # find the Plex section this lives under
        section = self._find_section(dir_path)

        lib_type = section.type.lower()  # e.g. "movie" or "show"
        if lib_type == "movie":
            return "movie"
        elif lib_type == "show":
            return "show"
        else:
            # fallback: if you ever add other libraries, treat them as movies by default
            return "movie"

    def scan_section(self, plex_path: PlexPath, cooldown: float = 0.5) -> None:
        section = self._find_section(plex_path)
        time.sleep(cooldown)  # avoid Plex API rate limits
        section.update(str(plex_path))
        logger.info(f"scanning section '{section.title}' for {plex_path}")

    def _find_section(self, directory: PlexPath, allow_deleted: bool = False):
        """
        Find the Plex library section for a given directory.
        
        Args:
            directory: The PlexPath to find the section for
            allow_deleted: If True, skip existence checks (for deleted paths)
        """
        for plex_root_path, section in self._roots:
            try:
                directory.path.relative_to(plex_root_path)
                return section
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")

    def _find_section_id(self, directory: PlexPath) -> int:
        """
        Locate which Plex section this directory belongs to,
        and return its numeric section-ID.
        """
        for plex_root, section in self._roots:
            try:
                # if `directory` is inside this plex_root, this will not throw
                directory.path.relative_to(plex_root)
                return int(section.key)
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")
