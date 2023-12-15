# TVthe(k)Index

Generates an index of tvthek downloaded content

## Usage (version 0.4.x)

Register at [TMDB](https://www.themoviedb.org/) and [get an API key](https://www.themoviedb.org/documentation/api).

### from binary (windows)

1. download binaries from [packages](https://gitlab.mplx.eu/scripts/tvthekidx/-/packages) and rename to `tvthekidx.exe`

2. create database

`tvthekidx.exe -v database -d tvthek.db -a create`

3. run the indexer
`tvthekidx.exe -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p x:\TVThek --add-unknown --recursive`
(insert you TMDB API key instead of `APIKEY`)

4. generate the html file
`tvthekidx.exe export -t "TVthek" -d tvthek.db -c "TVthek" -o tvthek.html`

5. if you add or remove content run steps 3 + 4 again

6. occasionally run the database maintainance

`./tvthekidx.exe -v database -d tvthek.db -a compress`

### from binary (linux)

1. download binaries from [packages](https://gitlab.mplx.eu/scripts/tvthekidx/-/packages) and rename to `tvthekidx`

2. make tvthekidx executeable
`chmod +x tvthekidx`

3. create database

`./tvthekidx -v database -d tvthek.db -a create`

4. run the indexer
`./tvthekidx -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --add-unknown --recursive`
(insert you TMDB API key instead of `APIKEY`)

5. generate the html file
`./tvthekidx export -t "TVthek" -d tvthek.db -c "TVthek" -o tvthek.html`

6. if you add or remove content run steps 4 + 5 again

7. occasionally run the database maintainance

`./tvthekidx -v database -d tvthek.db -a compress`

### from python source

1. download source code from [releases](https://gitlab.mplx.eu/scripts/tvthekidx/-/releases)

2. install requirements
`pip install -r requirements.txt`

2. create database

`python tvthekidx.py -v database -d tvthek.db -a create`

4. run the indexer
`python tvthekidx.py -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --add-unknown --recursive`
(insert you TMDB API key instead of `APIKEY`)

5. generate the html file
`python tvthekidx.py export -t "TVthek" -d tvthek.db -c "TVthek" -o tvthek.html`

6. if you add or remove content run steps 3 + 4 again

7. occasionally run the database maintainance

`python tvthekidx.py -v database -d tvthek.db -a compress`

## global arguments

- `-q` quiet (set verbose to 0)
- `-v` verbose

## `index` arguments

- `-d`, `--database` sqlite database
- `-p`, `--path` path to scan
- `-k`, `--key` TMDB API key
- `-t`, `--type` movies or tvshows (different API on TMDB; currently only movies supported)
- `-c`, `--collection` collection
- `-r`, `--recursive` recursive search
- `-a`, `--add-unknown` add unknown

## `export` arguments

- `-d`, `--database` sqlite database
- `-c`, `--collection` collection list (comma-separated)
- `-t`, `--title` page title
- `-o`, `--output` output file
- `--skip-actors` do not include actors section
- `--skip-header` do not include header with top and new sections

## `database` arguments

- `-d`, `--database` sqlite database
- `-a`, `--action` database actions: create, compress, upgrade
