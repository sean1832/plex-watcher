# Plex-Watcher
Plex-Watcher is a tool designed to monitor and manage media files in your Plex library. 
It automatically scans for new, modified, or deleted files and updates the Plex library accordingly.

## Installation
clone this repository and install the required dependencies:
```bash
git clone https://github.com/sean1832/plex-watcher.git
cd plex-watcher
pip install -e .
```


## Quick Start
To start using Plex-Watcher, run the following command in your terminal:
```bash
plex-watcher -p /path/media -s http://localhost:32400 -t token -i 10
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
| `-i`, `--interval` | int               | no (default `10`) | How long to sleep between filesystem polls, in seconds. Trade‑off: lower = faster response, higher = lower CPU wake‑ups. |
| `-v`, `--version`  | –                 | no                | Print the current `plex-watcher` version and exit.                                                                       |
| `-h`, `--help`     | –                 | no                | Show this help message and exit.                                                                                         |

## Usage
Usually you would run `plex-watcher` on a server where the media files are stored while plex server is running on a different server.

To run `plex-watcher` as a background service, you can use a process manager like `tmux`

```bash
tmux new -s plex-watcher
plex-watcher -p /path/to/media -s http://localhost:32400 -t TOKEN -i 5
```
- `ctrl+b d` to detach from the session
- `tmux attach -t plex-watcher` to reattach to the session
- `tmux ls` to list all sessions
- `tmux kill -t plex-watcher` to kill the session