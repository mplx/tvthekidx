# TVthekIndex

Generates an index of tvthek downloaded content

## Usage

1. install requirements
`pip install -r requirements.txt`
2. register at [TMDB](https://www.themoviedb.org/) and [get an API key](https://www.themoviedb.org/documentation/api)
3. run the indexer
`python tvthekidx.py -v index -k "APIKEY" -d tvthek.db -t movies -c "TVthek" -p /mnt/TVThek/ --add-unknown --recursive`
(insert you TMDB API key instead of `APIKEY`)
4. generate the html file
`python tvthekidx.py export -t "TVthek" -d tvthek.db -c "TVthek" -o tvthek.html`
5. if you add or remove content run steps 3 + 4 again

## global arguments

- `-q` quiet (set verbose to 0)
- `-v` verbose

## `index` arguments

- `-d`, `--database` sqlite database
- `-p`, `--path` path to scan
- `-t`, `--type` movies or tvshows (different API on TMDB; currently only movies supported)
- `-k`, `--key` TMDB API key
- `-c`, `--collection` collection
- `-r` recursive search
- `-a`, `--add-unknown` add unknown

## `export` arguments

- `-t`, `--title` pagetitle
- `-d`, `--database` sqlite database
- `-o`, `--output` output file
- `-c`, `--collection` collection
- `--skip-actors` do not include actors section
- `--skip-header` do not include header with top and new sections
