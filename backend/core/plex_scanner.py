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
        # 2) build your list of (plex_root_path, section)
        mapping = []
        for sec in self.sections.values():
            for loc in sec.locations:
                plex_root = Path(loc).resolve()
                mapping.append((plex_root, sec))
        # sort longest paths first (nested libs before top‐level)
        self._roots: list[tuple[Path, LibrarySection]] = sorted(
            mapping, key=lambda rs: len(str(rs[0])), reverse=True
        )

        for root, sec in self._roots:
            logger.info(f"Found Plex section: '{sec.title}' at {root}")

    def get_type(self, path: PlexPath) -> Literal["movie", "show"]:
        """
        Figure out whether a given file/folder belongs to your Movies or TV library,
        and return "movie" for a Movies section, or "show" for a TV Shows section.
        """
        # Use PlexPath's methods to check if it's a directory
        if path.is_dir():
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

    def _find_section(self, directory: PlexPath):
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
