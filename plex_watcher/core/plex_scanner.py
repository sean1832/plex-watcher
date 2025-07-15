import os
from pathlib import Path

from plexapi.server import PlexServer

from plex_watcher import logger


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
        self._roots = sorted(mapping, key=lambda rs: len(str(rs[0])), reverse=True)

        for root, sec in self._roots:
            logger.info(f"Found Plex section: '{sec.title}' at {root}")

    def scan_section(self, plex_path: str) -> None:
        section = self._find_section(Path(plex_path))
        section.update(plex_path)
        logger.info(f"scanning section '{section.title}' for {plex_path}")

    def _auto_map_to_plex(self, local_path: Path) -> Path:
        """
        Find the Plex root whose trailing path best matches a contiguous
        subsequence of local_path.parts (case-insensitive), then
        append any extra child segments.
        """
        # Strip out the leading slash so indexing lines up
        parts = [p for p in local_path.parts if p != os.sep]
        lower_parts = [p.lower() for p in parts]

        best_root = None
        best_k = 0
        best_children: tuple[str, ...] = ()

        for plex_root, _ in self._roots:
            plex_parts = [p for p in plex_root.parts if p != os.sep]
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
            return Path(*best_root.parts, *best_children)
        else:
            return local_path

    def _find_section(self, directory: Path):
        for plex_root_path, section in self._roots:
            try:
                directory.relative_to(plex_root_path)
                return section
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")

    def _find_section_id(self, directory: Path) -> int:
        """
        Locate which Plex section this directory belongs to,
        and return its numeric section‑ID.
        """
        for plex_root, section in self._roots:
            try:
                # if `directory` is inside this plex_root, this will not throw
                directory.relative_to(plex_root)
                return int(section.key)
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")
