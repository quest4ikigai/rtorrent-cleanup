# rtorrent-cleanup
A simple Python 3 script that:

- talks to rTorrent over your HTTP XML-RPC endpoint such as `http://127.0.0.1/RPC2`
- matches only torrents with labels "notes" or "whitepapers" (default)
- requires complete torrents
- requires 28 days (default) since `d.timestamp.finished`
- deletes the payload from disk
- then removes the torrent from rTorrent

It defaults to dry run mode.

## Setup
```bash
mkdir -p ~/scripts
nano ~/scripts/rtorrent_cleanup.py
chmod +x ~/scripts/rtorrent_cleanup.py
```

Recommended first test:
```bash
RTORRENT_RPC_URL='http://127.0.0.1/RPC2' DRY_RUN=1 ~/scripts/rtorrent_cleanup.py
```

If the matches look right, switch to live mode:
```bash
RTORRENT_RPC_URL='http://127.0.0.1/RPC2' DRY_RUN=0 ~/scripts/rtorrent_cleanup.py
```

Optionally, set a cron entry to run this daily. Example for running at 3:15 AM every day:
```cron
15 3 * * * RTORRENT_RPC_URL='http://127.0.0.1/RPC2' DRY_RUN=0 /home/myuser/scripts/rtorrent_cleanup.py
```

The script assumes you can reach rTorrent through an HTTP XML-RPC endpoint like /RPC2. That is the common ruTorrent setup behind a web server. rTorrent itself speaks XML-RPC and the docs cover that API, but if your install only exposes a raw SCGI socket and not an HTTP endpoint, you will need a different transport layer.

## Environment Variables

| Variable | Description | Default |
| ----------- | ----------- |  ----------- |
| RTORRENT_RPC_URL | The full HTTTP url of your rtorrent instance | http://127.0.0.1/RPC2 |
| LABELS | Comma separated list of labels | notes, whitepapers |
| MIN_AGE_DAYS | The minimum seeding time for a torrent | 28 |
| LOGFILE | Log file absolute path | ~/rtorrent_cleanup.log |
| DRY_RUN | Only execute a dry run | 1 |



## Some Important Notes

- `d.timestamp.finished` is the completion time in epoch seconds, so using 28 days from that is the right fit for the “finished downloading, then seed 4 weeks” rule.

- `d.custom1` is the ruTorrent label slot, so filtering "notes" and "whitepapers" there is the correct label check.

- rTorrent’s docs describe `d.directory` as always being a directory, and for single-file torrents the effective data path is `directory/name`, while for multi-file torrents it is the directory itself.

- `d.erase` removes the torrent item from rTorrent, but deleting payload files is something this script does itself on disk before calling `d.erase`.

- This script was AI generated but tested in a real environment.
