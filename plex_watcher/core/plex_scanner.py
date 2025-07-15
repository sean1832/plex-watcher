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

        # Determine directory to scan (parent if file)
        watcher_directory = watcher_path if watcher_path.is_dir() else watcher_path.parent
        watcher_directory = watcher_directory.resolve()

        # Map the local watcher directory to the Plex directory
        plex_directory = self._auto_map_to_plex(watcher_directory)

        # Find the Plex library section for this directory
        section = self._find_section(plex_directory)
        section.update(str(plex_directory))
        print(f"Partial scan: '{section.title}' -> {plex_directory}")

    def _auto_map_to_plex(self, watcher_directory: Path) -> Path:
        """Translate a local watcher directory into the Plex server's directory."""
        watcher_parts = watcher_directory.parts
        selected_plex_root = None
        longest_suffix_length = 0

        for plex_root_path, _ in self._roots:
            plex_parts = plex_root_path.parts
            # Compute length of common suffix
            max_suffix = min(len(plex_parts), len(watcher_parts))
            suffix_length = 0
            for idx in range(1, max_suffix + 1):
                if plex_parts[-idx] == watcher_parts[-idx]:
                    suffix_length += 1
                else:
                    break

            if suffix_length > longest_suffix_length:
                longest_suffix_length = suffix_length
                selected_plex_root = plex_root_path

        # If no matching suffix found, return the original
        if selected_plex_root is None or longest_suffix_length == 0:
            return watcher_directory

        # Rebuild mapped path: plex_root prefix + watcher suffix
        plex_root_prefix = selected_plex_root.parts[:-longest_suffix_length]
        watcher_suffix = watcher_parts[-longest_suffix_length:]
        mapped_directory = Path(*plex_root_prefix, *watcher_suffix).resolve()
        return mapped_directory

    def _find_section(self, p: Path):
        for root, sec in self._roots:
            try:
                p.relative_to(root)
                return sec
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{p}'")
