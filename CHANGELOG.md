# Changelog

## [unreleased]

### Added
- Genre support — genres fetched from TMDB and stored in `genres` / `movies_genres` tables; displayed as badges in HTML export
- `backfillgenres` maintenance action — fetches genres for existing movies that have none (requires `--key`, optional `--limit`)
- `refreshmovie` maintenance action — with `--tmdb-id` re-fetches one movie; without it runs a bulk refresh of top-20 by score + 20 random + 20 oldest-refreshed; stores a `refresh_timestamp` per movie
- `resetcounters` maintenance action — resets cast and genre error counters to zero for all movies
- Error counters (`cast_error_count`, `genre_error_count`) on movies — movies that return no results from TMDB are skipped after 3 consecutive failures per category
- **Streamer export plugin** (`--format streamer`) — multi-file, streaming-service-style export {coded by Anthropic's Sonnet 4.6}
- GitHub Release automation — pushing a version tag creates a release with auto-generated notes, Linux binary, and source distribution

### Changed
- Database schema v9

---

## [0.5.0] - 2026-05-05

### Added
- Export plugin system — format selectable via `--format`; `html` and `text` plugins included
- TV station detection — CNN-based identification of recording channel from screenshots; logos embedded in HTML export
- Tags — regex-based file tagging with new `tags` subcommand (`list`, `add`, `delete`, `export`)
- `maintenance` subcommand — replaces `database`; adds `detecttvstations`, `cleartvstations`, `getscreenshots`, `clearscreenshots` actions
- `--graphics` export option — `embed` (base64 inline, default), `reference` (external files), `disable`
- Clipboard copy button for filenames in HTML export
- Director display in movie detail view
- HTML generator meta tag

### Changed
- Database schema v8
- HTML export ~7× faster — bulk SQL queries replace per-movie/per-file round-trips; SQLite mmap and page-cache tuning reduces system time by ~190×
- CI pipeline upgraded to Debian trixie; win64 build removed; test matrix updated to bookworm and trixie
- `--url` flag added to HTML exporter for video hyperlink prefix
- Top list excludes 100%-scored movies
- Cover size and new-section entry count adjusted
- Sort order fixes for new section and movies-per-actor

### Fixed
- Badge width rendering
- JavaScript search escaping and keybinding
- Invalid TMDB ID query handling

---

## [0.4.0] - 2024-01-08

### Added
- Screenshot capture via ffprobe/moviepy
- `database maintenance` command
- File detail view for single-collection exports
- MIT license

### Changed
- Restructured into Python package (`src/` layout) for use with setuptools
- ffprobe used for video metadata extraction
- Packaging switched to `pyproject.toml` / `python -m build`
- Linter (flake8/pylint) added to CI

---

## [0.3.2] - 2023-08-23

### Changed
- PyInstaller version bump

---

## [0.3.1] - 2023-08-16

### Added
- Search keyboard shortcut

---

## [0.3.0] - 2023-08-15

### Added
- Simple full-text search in HTML export
- Test of Linux binary on Debian bookworm

---

## [0.2.0] - 2023-07-24

### Added
- File size shown in collection hover tooltip
- GitLab build pipeline

### Changed
- Movies-per-actor sort order updated

---

## [0.1.0] - 2022-11-30

### Added
- HTML navbar and "new releases" section
- Merged scripts into single entry point

### Changed
- Switched from getopt to argparse
- Increased entry count in new section

---

## [0.0.6] - 2022-02-19

### Fixed
- Word-break rendering and debug output removed

---

## [0.0.5] - 2022-02-16

### Added
- Collections support
- Actors section
- Non-TMDB files listed in output
- Release pipeline
- Custom header

### Changed
- Refactored codebase
- Strict title matching; SQL escaping fixes
- UTF-8 output enforced
