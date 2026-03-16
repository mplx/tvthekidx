# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu


from . utility import verbose

from tmdbv3api import TMDb
from tmdbv3api import Movie
from tmdbv3api import Search

from urllib.request import urlopen


def initialize_tmdb(apikey, language="de"):
    tmdb = TMDb()
    tmdb.api_key = apikey

    tmdb.language = language
    tmdb.debug = True

    movie = Movie()
    search = Search()

    return movie, search


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


def query_cast(movie, tmdbid):
    # query actors
    verbose("Querying movie cast online...", 2)
    cast = []
    crew = []
    try:
        results = movie.credits(tmdbid)
        # parse result
        for c in results['cast']:
            person = {
                "name": c['name'],
                "photo": c['profile_path'],
                "popularity": c['popularity'],
                "tmdb_id": c['id'],
                "profile": fetchPoster(c['profile_path'])
            }
            cast.append(person)
        # parse result
        for c in results['crew']:
            person = {
                "name": c['name'],
                "photo": c['profile_path'],
                "popularity": c['popularity'],
                "tmdb_id": c['id'],
                "profile": fetchPoster(c['profile_path']),
                "job": c['job']
            }
            if (person['job'] == "Director"):
                crew.append(person)
        # sort cast by popularity
        cast.sort(key=actor_get_popularity, reverse=True)
    except:
        verbose(f'Error querying movie online: TMDBID={tmdbid}')
    return cast, crew


def query_movie(search, name, year):
    verbose(f'Querying movie online: {name} {year}', 2)
    query = {"query": name, "year": year}
    results = search.movies(query)
    if isinstance(results, list):
        if len(results) == 0:
            return None
        else:
            for m in results:
                if m['title'] == name and int(m['release_date'][0:4]) == year:
                    return m
            # no exact match found
            return results[0]
    else:
        return results
