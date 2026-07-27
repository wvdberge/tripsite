# Tripsite

Private, LAN-only trip-planning site for the NZ 2027 trip. Flask + SQLite +
Jinja2 + htmx, Leaflet map. Two users, no passwords. See `PLAN.md` for the
full design and locked decisions.

## Run locally

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python import_data.py --wipe --partner "NAME"   # one-time seed
./.venv/bin/python app.py                                   # http://127.0.0.1:5000
```

The DB path defaults to `./data/trip.db`; override with `TRIPSITE_DB`.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask routes + helpers |
| `db.py` | connection, schema init, event logging |
| `schema.sql` | table definitions |
| `import_data.py` | one-time importer (`--wipe` re-imports from scratch) |
| `seed/places.py` | place-name → lat/lon lookup (no geocoding API) |
| `templates/`, `static/` | Jinja2 views; vendored htmx + Leaflet |
| `Dockerfile`, `docker-compose.yml` | container image + build |
| `.github/workflows/` | build + push image to ghcr.io on every push to main |
| `sync_db.sh` | pull the latest NAS backup into this folder |

## Deploy to the Synology NAS (git clone + Container Manager)

Same workflow as the budget and portfolio apps: the code is a public GitHub
repo, cloned straight onto the NAS and built there. The NAS is `mynas`
(192.168.1.202). Docker needs `sudo`. Reach the site at
`http://192.168.1.202:8027` on home wifi. The `data/` folder is gitignored and
seeded on the NAS, so no personal data (partner name, notes) ever hits GitHub.

1. **Clone onto the NAS** (SSH in; cloning needs no sudo):

   ```sh
   ssh mynas
   cd /volume1/docker
   git clone https://github.com/wvdberge/tripsite.git
   ```

2. **Build + start the container** (`sudo` needed):

   ```sh
   cd /volume1/docker/tripsite
   sudo docker compose up -d --build     # or: sudo docker-compose up -d --build
   ```

3. **Seed the database once** — runs the importer inside the container, so the
   partner's name stays off GitHub:

   ```sh
   sudo docker exec tripsite python import_data.py --wipe --partner "NAME"
   ```

   Open `http://192.168.1.202:8027`, pick your name, and it's live.

4. **Update to a new version** (never touches `data/`):

   ```sh
   cd /volume1/docker/tripsite && git pull && sudo docker compose up -d --build
   ```

5. **Nightly backup** — DSM → Control Panel → Task Scheduler → Create →
   Scheduled Task → User-defined script, daily, run as `root`:

   ```sh
   mkdir -p /volume1/docker/tripsite/backup
   /usr/bin/sqlite3 /volume1/docker/tripsite/data/trip.db \
     ".backup /volume1/docker/tripsite/backup/trip-$(date +%F).db"
   find /volume1/docker/tripsite/backup -name 'trip-*.db' -mtime +30 -delete
   ```

   Keep `/volume1/docker/tripsite/backup` inside the existing 3-2-1 backup scope.

6. **Occasional repo snapshot** of the live DB:

   ```sh
   ./sync_db.sh   # scp's the newest NAS backup to ./trip-backup.db
   ```
