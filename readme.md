# Plex-Watcher
Plex-Watcher is a tool designed to monitor and manage media files in your Plex library. 
It automatically scans for new, modified, or deleted files and updates the Plex library accordingly.

(This is an interal tool for personal use, not intended for public distribution.)


## Quick Start
To start using Plex-Watcher, run the following command in your terminal:
```bash
plex-watcher -p /path/media -s http://localhost:32400 -t token -i 30
```
If you need help with the command-line options, you can run:
```bash
plex-watcher -h
```


## Command-Line Interface
```
plex-watcher [-p DIR]... -s URL -t TOKEN [-i SECONDS] [-v]
```
| Flag               | Type              | Required          | Description                                                                                                              |
| ------------------ | ----------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `-p`, `--path`     | Path (repeatable) | **yes**           | Directory to watch. Pass the flag multiple times to add more roots.                                                      |
| `-s`, `--server`   | string            | **yes**           | Base URL of your Plex server (e.g. `http://192.168.1.10:32400`).                                                         |
| `-t`, `--token`    | string            | **yes**           | Plex authentication token. Generate one from *Account → Authorized Devices* in Plex.                                     |
| `-i`, `--interval` | int               | no (default `30`) | How long to sleep between filesystem polls, in seconds. Trade‑off: lower = faster response, higher = lower CPU wake‑ups. |
| `-v`, `--version`  | –                 | no                | Print the current `plex-watcher` version and exit.                                                                       |
| `-h`, `--help`     | –                 | no                | Show this help message and exit.                                                                                         |