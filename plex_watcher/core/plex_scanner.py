import os
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
        Find the Plex root whose trailing path best matches a contiguous
        subsequence of local_path.parts (case‑insensitive), then
        append any extra child segments.
        """
        local_parts = [p.lower() for p in local_path.parts if p not in (os.sep,)]
        best_root = None
        best_k = 0
        best_children = ()

        for plex_root, _ in self._roots:
            plex_parts = [p.lower() for p in plex_root.parts if p not in (os.sep,)]
            max_k = min(len(plex_parts), len(local_parts))

            # try from longest suffix→shortest
            for k in range(max_k, 0, -1):
                suffix = plex_parts[-k:]
                # look for this suffix anywhere in local_parts
                for idx in range(len(local_parts) - k + 1):
                    if local_parts[idx : idx + k] == suffix:
                        # record children beyond the match
                        children = local_path.parts[idx + k :]
                        if k > best_k:
                            best_root = plex_root
                            best_k = k
                            best_children = children
                        # once matched this k, no need to slide idx further
                        break
                if best_k == k:
                    # found the longest possible for this root
                    break

        if best_root and best_k > 0:
            return Path(*best_root.parts, *best_children)
        else:
            # fallback if nothing aligns
            return local_path

    def _find_section(self, directory: Path):
        for plex_root_path, section in self._roots:
            try:
                directory.relative_to(plex_root_path)
                return section
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{directory}'")
