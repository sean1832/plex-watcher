from pathlib import Path

from plexapi.server import PlexServer


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
            print(f"Found Plex section: '{sec.title}' at {root}")

    def scan_partial(self, path: str) -> None:
        """Scan the directory containing `path`, mapping watcher paths to Plex paths automatically."""
        watcher_path = Path(path)
        if not watcher_path.exists():
            raise FileNotFoundError(f"Path '{path}' does not exist.")

        # If it's a file, start from its parent; otherwise the directory itself
        start_dir = watcher_path if watcher_path.is_dir() else watcher_path.parent

        # Walk up through ancestors to find a matching Plex section
        for candidate_dir in (start_dir, *start_dir.parents):
            resolved_dir = candidate_dir.resolve()
            mapped_dir = self._auto_map_to_plex(resolved_dir)
            try:
                section = self._find_section(mapped_dir)
                section.update(str(mapped_dir))
                print(f"Partial scan: '{section.title}' -> {mapped_dir}")
                return
            except ValueError:
                continue

        raise ValueError(f"No Plex section found for '{watcher_path}'")

    def _auto_map_to_plex(self, local_path: Path) -> Path:
        """
        Automatically map a local filesystem path (e.g., NFS mount) to the Plex
        server's internal path structure by matching subpath structure.
        """
        local_path = local_path.resolve()
        best_match = None
        best_match_length = -1
        mapped_result = local_path

        for plex_root_path, _ in self._roots:
            plex_parts = plex_root_path.parts

            for i in range(len(plex_parts)):
                suffix = plex_parts[i:]
                if local_path.parts[-len(suffix) :] == suffix:
                    prefix = plex_root_path.parts[:i]
                    local_suffix = local_path.parts[-len(suffix) :]
                    mapped_result = Path(*prefix, *local_suffix)
                    if len(suffix) > best_match_length:
                        best_match = mapped_result
                        best_match_length = len(suffix)

        return best_match if best_match else local_path

    def _find_section(self, directory: Path):
        for plex_root_path, section in self._roots:
            try:
                directory.relative_to(plex_root_path)
                return section
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")
