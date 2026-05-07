# TVthe(k)Index

Generates an index of tvthek/mediathek downloaded content and queries [TMDB](https://www.themoviedb.org/) for the meta data

![TVthe(k)Index Logo](https://raw.githubusercontent.com/mplx/tvthekidx/main/docs/assets/tvthekidx.png)

## Example

[![TVthe(k)Index Sample](https://raw.githubusercontent.com/mplx/tvthekidx/main/docs/assets/sample.png)](https://peach.blender.org/)

## Usage (version 0.5.0)

### Prerequisites

Register at [TMDB](https://www.themoviedb.org/) and [get an API key](https://www.themoviedb.org/documentation/api).

### from PyPI

1. install

`pip install tvthekidx`

2. create database

`tvthekidx -v maintenance -d tvthek.db -a createdb`

3. run the indexer

`tvthekidx -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --recursive`

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

(insert your TMDB API key instead of `APIKEY`)

5. generate the html file

`tvthekidx export -d tvthek.db -c "TVthek" -f html --title "TVthek" --output tvthek.html`

6. if you add or remove content run steps 4 + 5 again

7. occasionally run database maintenance

`tvthekidx -v maintenance -d tvthek.db -a compressdb`

## Global arguments

- `-q`, `--quiet` quiet (set verbose to 0)
- `-v`, `--verbose` increase verbosity (stackable)

## `index` arguments

- `-d`, `--database` SQLite database file
- `-p`, `--path` path to scan for video files
- `-k`, `--key` TMDB API key
- `-t`, `--type` content type (`movies`; tvshows not yet supported)
- `-c`, `--collection` collection name
- `-r`, `--recursive` scan subdirectories recursively

## `export` arguments

- `-d`, `--database` SQLite database file
- `-c`, `--collection` comma-separated list of collections to include
- `-f`, `--format` export format plugin (`html`, `text`); default `html`

### HTML plugin arguments (passed after `export`)

- `--title` page title
- `--output`, `-o` output file (default `tvthek.html`)
- `--graphics` image handling: `embed` (default, base64 inline), `reference` (external files), `disable`
- `--skip-actors` omit the actors/crew section
- `--skip-header` omit the top-rated and newest-additions header sections
- `--url` hyperlink prefix for video file links (default `./`)

## `maintenance` arguments

- `-d`, `--database` SQLite database file
- `-a`, `--action` one of:
  - `createdb` — create a new database
  - `upgradedb` — run schema migrations on an existing database
  - `compressdb` — deduplicate movies and VACUUM
  - `detecttvstations` — run ML-based TV station detection on stored screenshots
  - `cleartvstations` — remove all TV station assignments
  - `getscreenshots` — capture/backfill screenshots for files (requires `-p`)
  - `clearscreenshots` — delete all stored screenshots
  - `backfillgenres` — fetch genres from TMDB for all movies that don't have them yet (requires `-k`, optional `-l`)
  - `refreshmovie` — re-fetch all metadata (description, rating, poster, genres, cast/crew) for one movie from TMDB (requires `-k` and `--tmdb-id`)
  - `resetcounters` — reset cast and genre error counters to zero
- `-p`, `--path` path to video files (required for `getscreenshots`)
- `-c`, `--collection` collection filter (optional for `getscreenshots`)
- `-k`, `--key` TMDB API key (required for `backfillgenres` and `refreshmovie`)
- `--tmdb-id` TMDB movie ID (required for `refreshmovie`)
- `-l`, `--limit` maximum number of movies to process per run (for `backfillgenres`, to stay within TMDB API rate limits)

## `tags` arguments

- `-d`, `--database` SQLite database file
- `-a`, `--action` one of: `list`, `add`, `delete`, `export`
- `-t`, `--tag` tag name
- `-r`, `--regex` regular expression pattern matched against filenames
- `--all` delete all tags (use with `--action delete`)

## Development

```bash
pip install -e .                 # install with runtime dependencies
pip install -r requirements-dev.txt  # dev tools (pytest, flake8, pylint, build)
pytest                           # run unit tests
flake8 src/
pylint src/
python -m build                  # build sdist + wheel
```
