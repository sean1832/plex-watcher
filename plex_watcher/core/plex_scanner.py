from pathlib import Path

from plexapi.server import PlexServer

class PlexScanner:
    def __init__(self, plex: PlexServer):
        self.plex = plex

        # 1) Fetch all sections once
        self.sections = {
            sec.title: sec for sec in plex.library.sections()
        }  # :contentReference[oaicite:0]{index=0}
        # 2) Build and sort your root-path → section mapping
        mapping = []
        for sec in self.sections.values():
            for loc in sec.locations:  # :contentReference[oaicite:1]{index=1}
                root = Path(loc).resolve()
                mapping.append((root, sec))
        # sort so deepest paths come first (to handle nested libraries)
        self._roots = sorted(mapping, key=lambda x: len(str(x[0])), reverse=True)

    def scan_partial(self, path: str | Path) -> None:
        """Scan a specific library section.

        Args:
            path (str|Path): The path to scan.

        Raises:
            FileNotFoundError: If the specified path does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Path '{path}' does not exist.")
        section = self._find_section(p.resolve())
        section.update(str(p))  # only rescans that folder
        print(f"Partial scan: '{section.title}' -> {p}")

    def _find_section(self, p: Path):
        for root, sec in self._roots:
            try:
                p.relative_to(root)
                return sec
            except ValueError:
                continue
        raise ValueError(f"No Plex section found for '{p}'")
