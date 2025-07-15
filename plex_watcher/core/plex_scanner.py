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
            plex_dir = self._auto_map_to_plex(resolved_dir)
            try:
                section = self._find_section(plex_dir)
                section.update(str(plex_dir))
                print(f"Partial scan: '{section.title}' -> {plex_dir}")
                return
            except ValueError:
                # Not a valid Plex section, continue up
                continue

        # If no section was matched
        raise ValueError(f"No Plex section found for '{watcher_path}'")

    def _auto_map_to_plex(self, watcher_directory: Path) -> Path:
        """Translate a local watcher directory into the Plex server's directory."""
        watcher_parts = watcher_directory.parts
        selected_plex_root = None
        longest_suffix_length = 0

        for plex_root_path, _ in self._roots:
            plex_parts = plex_root_path.parts
            # Match longest common suffix segments
            max_check = min(len(plex_parts), len(watcher_parts))
            suffix_length = 0
            for i in range(1, max_check + 1):
                if plex_parts[-i] == watcher_parts[-i]:
                    suffix_length += 1
                else:
                    break

            if suffix_length > longest_suffix_length:
                longest_suffix_length = suffix_length
                selected_plex_root = plex_root_path

        # If no suffix match, return the original watcher path
        if not selected_plex_root or longest_suffix_length == 0:
            return watcher_directory

        # Build mapped path: prefix of Plex root + matching suffix
        prefix = selected_plex_root.parts[:-longest_suffix_length]
        suffix = watcher_parts[-longest_suffix_length:]
        return Path(*prefix, *suffix).resolve()

    def _find_section(self, directory: Path):
        for plex_root_path, section in self._roots:
            try:
                directory.relative_to(plex_root_path)
                return section
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")
