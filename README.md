# TVthe(k)Index

Generates an index of tvthek/mediathek downloaded content and queries [TMDB](https://www.themoviedb.org/) for the meta data

![TVthe(k)Index Logo](https://raw.githubusercontent.com/mplx/tvthekidx/main/docs/assets/tvthekidx.png)

## Example

[![TVthe(k)Index Sample](https://raw.githubusercontent.com/mplx/tvthekidx/main/docs/assets/sample.png)](https://peach.blender.org/)

## Usage (version 0.6.0)

### Prerequisites

- Python 3.9 or newer
- `ffmpeg` and `ffprobe` installed and on the `PATH` (used for video metadata and screenshots). On Windows, download a build from [ffmpeg.org](https://ffmpeg.org/download.html) and add its `bin` folder to the `PATH`; `ffprobe -version` should work in a new console.
- Register at [TMDB](https://www.themoviedb.org/) and [get an API key](https://www.themoviedb.org/documentation/api).

### from PyPI

1. install

`pip install tvthekidx`

2. create database

`tvthekidx -v maintenance -d tvthek.db -a createdb`

3. run the indexer

`tvthekidx -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --recursive`

To index TV shows:

`tvthekidx -v index -k "APIKEY" -d tvthek.db -t tvshows -c "TVthek" -p /mnt/TVThek/ --recursive`

(insert your TMDB API key instead of `APIKEY`)

4. generate the html file

`tvthekidx export -d tvthek.db -c "TVthek" -f html --title "TVthek" --output tvthek.html`

5. if you add or remove content run steps 3 + 4 again

6. occasionally run database maintenance

`tvthekidx -v maintenance -d tvthek.db -a compressdb`

### from python source

1. download source code from [tags](https://github.com/mplx/tvthekidx/tags)

2. install requirements

`pip install -e .`

3. create database

`tvthekidx -v maintenance -d tvthek.db -a createdb`

4. run the indexer

`tvthekidx -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --recursive`

To index TV shows:

`tvthekidx -v index -k "APIKEY" -d tvthek.db -t tvshows -c "TVthek" -p /mnt/TVThek/ --recursive`

(insert your TMDB API key instead of `APIKEY`)

5. generate the html file

`tvthekidx export -d tvthek.db -c "TVthek" -f html --title "TVthek" --output tvthek.html`

6. if you add or remove content run steps 4 + 5 again

7. occasionally run database maintenance

`tvthekidx -v maintenance -d tvthek.db -a compressdb`

### Upgrading from 0.5.0

`pip install --upgrade tvthekidx`

- **Back up your database file first.** The first command that opens it (`index`, `export`, `maintenance` or `tags`) upgrades the schema from version 8 to 15.
- The stable id column is renamed from `oid` to `guid`. `oid` is a reserved alias in SQLite, and SQLite 3.54 and newer refuse to create such a column, which broke new databases. Existing values are kept, so exported page URLs stay the same.
- Movies that were indexed twice under different file names (same TMDB id) are merged into one entry during the upgrade. Run with `-v` to see which ones.
- Each upgrade step either completes or is rolled back. If a step fails, the command stops with an error that names the step, and the database stays at the previous version.
- `moviepy` and `ffmpeg-python` are no longer used; `ffmpeg` and `ffprobe` must be on the `PATH` instead (see Prerequisites).

## Global arguments

- `-q`, `--quiet` quiet (set verbose to 0)
- `-v`, `--verbose` increase verbosity (stackable)

## `index` arguments

- `-d`, `--database` SQLite database file
- `-p`, `--path` path to scan for video files
- `-k`, `--key` TMDB API key
- `-t`, `--type` content type: `movies` (default) or `tvshows`
- `-c`, `--collection` collection name
- `-r`, `--recursive` scan subdirectories recursively

> **Filename convention:** By default, video files must be named `Title (YYYY).ext` (e.g. `Metropolis (1927).mkv`). An optional `{StationKey}` tag anywhere after the year is also captured (e.g. `News (2024) {ARD}.mkv`). TV show files must additionally include a season/episode tag, e.g. `Show Title (2022) S01E03.mkv`. Custom per-collection regexes can be stored with the `setcollectionregex` maintenance action.

## `export` arguments

- `-d`, `--database` SQLite database file
- `-c`, `--collection` comma-separated list of collections to include
- `-f`, `--format` export format plugin (`html`, `text`, `streamer`); default `html`

### HTML plugin arguments (passed after `export`)

- `--title` page title
- `--output`, `-o` output file (default `tvthek.html`)
- `--graphics` image handling: `embed` (default, base64 inline), `reference` (external files), `disable`
- `--skip-actors` omit the actors/crew section
- `--skip-header` omit the top-rated and newest-additions header sections
- `--url` hyperlink prefix for video file links (default `./`)

### Text plugin arguments (passed after `export`)

- `--output`, `-o` output file (default: standard output)

### Streamer plugin arguments (passed after `export`)

Generates a multi-file, streaming-service-style site (Netflix/Prime aesthetic) as a directory tree. All images are embedded in the pages.

- `--targetpath` output directory (required; must not exist unless `--overwrite` is given)
- `--title` site title (default `TVThek Index`)
- `--jellyfin` Jellyfin base URL, e.g. `http://10.1.2.3:8096` - adds a play button on each movie page
- `--overwrite` write into an existing output directory

**Output structure:**
```
<targetpath>/
├── index.html              search + carousels (Zufall, Neu, Top, per-genre, Serien, Personen, Tags, TV-Sender)
├── new.html, top.html      250 newest / 250 best-rated movies
├── random.html             250 random movies, sortable
├── assets/
│   ├── style.css
│   ├── app.js
│   └── search.js           search index (generated, not static)
├── media/
│   └── <x>/                sharded by first character of the guid
│       └── <guid>.html     movie page
├── shows/
│   └── <x>/
│       ├── <guid>.html     show page (hero + cast + seasons overview)
│       └── <guid>_s<n>.html season page (episode list)
├── persons/
│   └── <x>/
│       └── <guid>.html     actor / director page
├── genres/
│   ├── <guid>.html         one page per genre
│   └── <d>/<year>.html     one page per release year, sharded by first digit
├── tags/                   one .html per tag
└── tvstations/             one .html per TV station
```

Each movie page includes an "Ähnliche Filme" carousel of the 20 most similar movies, scored by genres (50 %), shared persons (20 %), tags (15 %), and score proximity (15 %), plus an "Ähnliche Serien" carousel.

Each season page lists the episodes: **green** has a local file, **yellow** is known to TMDB but missing locally, **orange** is a local file that TMDB does not know, **red** is a gap in TMDB's own episode numbering.

**Example:**
```bash
tvthekidx export -d tvthek.db -c "TVthek" -f streamer \
  --targetpath /var/www/html --jellyfin http://10.1.2.3:8096
```

## `maintenance` arguments

- `-d`, `--database` SQLite database file
- `-a`, `--action` one of:
  - `createdb` - create a new database
  - `upgradedb` - run schema migrations on an existing database (every command also does this automatically)
  - `compressdb` - deduplicate movies and VACUUM
  - `detecttvstations` - run ML-based TV station detection on stored screenshots (needs `pip install "tvthekidx[tvstation]"`)
  - `cleartvstations` - remove all TV station assignments
  - `getscreenshots` - capture/backfill screenshots for files (requires `-p`)
  - `clearscreenshots` - delete all stored screenshots
  - `backfillgenres` - fetch genres from TMDB for all movies that don't have them yet (requires `-k`, optional `-l`)
  - `backfilltvgenres` - fetch genres from TMDB for all TV shows that don't have them yet (requires `-k`, optional `-l`)
  - `refreshmovie` - re-fetch metadata for one movie (with `--tmdb-id`) or run a bulk refresh of top-10 by score + 10 random + 10 oldest-refreshed movies (without `--tmdb-id`); stores a refresh timestamp per movie; requires `-k`
  - `refreshtvshow` - re-fetch metadata for one TV show (with `--tmdb-id`) or run a bulk refresh (without `--tmdb-id`); requires `-k`
  - `resetcounters` - reset cast, genre, and season error counters to zero for all movies and TV shows
  - `setcollectionregex` - store a custom filename regex for a collection (requires `-c`; at least one of `--movie-regex` or `--tvshow-regex`); regex must use named groups `(?P<name>...)` and `(?P<year>...)` (movie), plus `(?P<season>...)` and `(?P<episode>...)` (tvshow); `(?P<tvstation>...)` is optional in both
- `-p`, `--path` path to video files (required for `getscreenshots`)
- `-c`, `--collection` collection name (required for `setcollectionregex`; optional for `getscreenshots`)
- `-k`, `--key` TMDB API key (required for `backfillgenres`, `backfilltvgenres`, `refreshmovie` and `refreshtvshow`)
- `--tmdb-id` TMDB movie or TV show ID (optional for `refreshmovie` / `refreshtvshow`; omit for bulk refresh)
- `-l`, `--limit` maximum number of movies or TV shows to process per run (for `backfillgenres` / `backfilltvgenres`, to stay within TMDB API rate limits)
- `--movie-regex` custom movie filename regex with named groups (for `setcollectionregex`)
- `--tvshow-regex` custom TV-show filename regex with named groups (for `setcollectionregex`)

## `tags` arguments

- `-d`, `--database` SQLite database file
- `-a`, `--action` one of: `list`, `add`, `delete`, `export`
- `-t`, `--tag` tag name
- `-r`, `--regex` regular expression pattern matched against filenames
- `--all` delete all tags (use with `--action delete`)

## Troubleshooting

- **See what it is doing:** add `-v` before the subcommand (`tvthekidx -v index ...`). It logs every file and every TMDB lookup.
- **A file or request hangs:** probing a video and grabbing a screenshot give up after 60 s and 120 s, TMDB requests after 30 s. The file is logged as failed and the scan continues.
- **Running tvthekidx from another program** (a script that reads its output through a pipe): output is written line by line. Set `PYTHONIOENCODING=utf-8` for tvthekidx and decode its output as UTF-8. Otherwise umlauts appear as two characters (`Ã¼` instead of `ü`), and on Windows titles with characters outside the code page can stop the run.

## Development

```bash
pip install -e ".[dev]"              # runtime + dev tools (pytest, flake8, pylint, build, pyinstaller)
pip install -e ".[tvstation]"        # optional: TV station detection (ultralytics)
pytest                               # run unit tests
flake8 src/tvthekidx/*.py --ignore=E501,E722,W503,W504
pylint --errors-only --disable import-error src/tvthekidx/*.py
python -m build                      # build sdist + wheel
pyinstaller tvthekidx.spec           # build the single-file binary
```
