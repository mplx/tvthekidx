# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu


from . utility import verbose

from tmdbv3api import TMDb
from tmdbv3api import Movie
from tmdbv3api import Search
from tmdbv3api import Season
from tmdbv3api import TV

from urllib.request import urlopen


def initialize_tmdb(apikey, language="de"):
    tmdb = TMDb()
    tmdb.api_key = apikey

    tmdb.language = language
    tmdb.debug = True

    movie = Movie()
    search = Search()
    tv = TV()

    return movie, search, tv


def fetchPoster(posterPath):
    # https://image.tmdb.org/t/p/w200/zWRlFDY03muF921z39Xg7Py5WRK.jpg
    baseurl = 'https://image.tmdb.org/t/p/w154'
    if posterPath:
        url = baseurl + posterPath
        poster = urlopen(url).read()
        return poster
    else:
        return None


def actor_get_popularity(actor):
    popularity = actor.get('popularity')
    return popularity


def query_cast(movie_api, tmdbid):
    # query actors — raises on API/network failure
    verbose("Querying movie cast online...", 2)
    cast = []
    crew = []
    results = movie_api.credits(tmdbid)
    for c in results['cast']:
        try:
            cast.append({
                "name": c['name'],
                "photo": c['profile_path'],
                "popularity": c['popularity'],
                "tmdb_id": c['id'],
                "profile": fetchPoster(c['profile_path'])
            })
        except Exception:
            pass
    for c in results['crew']:
        try:
            if c['job'] in ("Director", "Writer"):
                crew.append({
                    "name": c['name'],
                    "photo": c['profile_path'],
                    "popularity": c['popularity'],
                    "tmdb_id": c['id'],
                    "profile": fetchPoster(c['profile_path']),
                    "job": c['job']
                })
        except Exception:
            pass
    # sort cast by popularity
    cast.sort(key=actor_get_popularity, reverse=True)
    return cast, crew


def query_movie_by_id(movie_api, tmdbid):
    verbose(f'Querying movie details online: {tmdbid}', 2)
    return movie_api.details(tmdbid)


def query_genres(movie_api, tmdbid):
    verbose(f'Querying genres online: {tmdbid}', 2)
    result = movie_api.details(tmdbid)
    genres = result.get('genres', [])
    return [{"id": g['id'], "name": g['name']} for g in genres] if genres else []


def query_movie(search, name, year):
    verbose(f'Querying movie online: {name} {year}', 2)
    # tmdbv3api 1.9.0 returns AsObj wrapping the full response; when results is
    # empty its __iter__ falls back to dict-key strings — filter to real items only.
    items = [m for m in search.movies(name, year=year) if hasattr(m, 'get')]
    if not items:
        return None
    for m in items:
        try:
            if m['title'] == name and int(m['release_date'][0:4]) == year:
                return m
        except (KeyError, ValueError, TypeError):
            pass
    return items[0]


def query_tvshow(search, name, year):
    verbose(f'Querying TV show online: {name} {year}', 2)
    items = [r for r in search.tv_shows(name) if hasattr(r, 'get')]
    if not items:
        return None
    for r in items:
        first_air = r.get('first_air_date') or ''
        r_year = int(first_air[:4]) if len(first_air) >= 4 else 0
        if r.get('name') == name and r_year == year:
            return r
    return items[0]


def query_tvshow_by_id(tv, tmdbid):
    verbose(f'Querying TV show details online: {tmdbid}', 2)
    return tv.details(tmdbid)


def query_tvshow_credits(tv, tmdbid):
    verbose(f'Querying TV show credits online: {tmdbid}', 2)
    cast = []
    crew = []
    results = tv.credits(tmdbid)
    for c in results.get('cast', []):
        try:
            cast.append({
                "name": c['name'],
                "photo": c.get('profile_path'),
                "popularity": c.get('popularity', 0),
                "tmdb_id": c['id'],
                "profile": fetchPoster(c.get('profile_path'))
            })
        except Exception:
            pass
    for c in results.get('crew', []):
        try:
            if c.get('job') not in ("Director", "Writer"):
                continue
            crew.append({
                "name": c['name'],
                "photo": c.get('profile_path'),
                "popularity": c.get('popularity', 0),
                "tmdb_id": c['id'],
                "profile": fetchPoster(c.get('profile_path')),
                "job": c.get('job', '')
            })
        except Exception:
            pass
    cast.sort(key=actor_get_popularity, reverse=True)
    return cast, crew


def query_tvshow_season(tv, tmdbid, season_number):
    verbose(f'Querying TV season online: {tmdbid} S{season_number}', 2)
    result = Season().details(tmdbid, season_number)
    episodes = []
    for ep in result.get('episodes', []):
        try:
            air_date = ep.get('air_date') or ''
            year = int(air_date[:4]) if len(air_date) >= 4 else None
            episodes.append({
                "episode_number": ep['episode_number'],
                "title": ep.get('name'),
                "year": year,
                "description": ep.get('overview'),
                "score": float(ep.get('vote_average') or 0.0) * 10,
            })
        except (KeyError, ValueError, TypeError):
            pass
    return episodes
