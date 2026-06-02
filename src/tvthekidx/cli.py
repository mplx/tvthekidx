#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import argparse
import os
import re
import sys

from . import database, export, files, online, tags
from ._version import __version__
from .utility import getVerbosity, setVerbosity, verbose


def indexer(args, remaining=None):
    if args.libType != "movies":
        print(
            "ERROR: currently only type 'movies' supported (tvshows require a different TMDB API)"
        )
        sys.exit(2)

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    verbose(f"Indexing path '{args.libPath}' for collection '{args.collection}'")
    db = database.initialize_db(args.dbfile)
    movie, search = online.initialize_tmdb(args.tmdbApiKey)

    files.scanDir(db, args.collection, args.libPath, args.recursiveSearch)
    database.scanMovies(db, search)
    database.scanCredits(db, movie)
    database.scanGenres(db, movie)


def exporter(args, remaining):
    collection = args.collectionStr.split(",") if args.collectionStr else None

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    col_display = ', '.join(collection) if collection else 'all'
    verbose(f"Exporting collection '{col_display}' using format '{args.format}'")
    db = database.create_connection(args.dbfile)
    plugin = export.load_exporter(args.format)
    plugin_args = plugin.parse_args(remaining)
    plugin.export(db, collection, args, plugin_args)


def maintenance(args, remaining=None):
    if args.action == "createdb":
        if os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' already exists")
            sys.exit(2)
        verbose("Creating database")
        database.initialize_db(args.dbfile)
        return

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)
    db = database.create_connection(args.dbfile)

    if args.action == "compressdb":
        verbose("Compressing database")
        database.cleanup_db(db)
    elif args.action == "upgradedb":
        verbose("Upgrading database schema")
        database.upgrade_db(args.dbfile)

    elif args.action == "detecttvstations":
        verbose("Detecting TV stations from screenshots")
        from . import tvstation
        model = tvstation.load_model()
        if model is None:
            print("ERROR: ultralytics is not installed or model file not found (pip install 'tvthekidx[tvstation]')")
            sys.exit(2)
        tvstation.backfill_tvstation(db, model)
    elif args.action == "cleartvstations":
        verbose("Clearing TV station assignments")
        from . import tvstation
        tvstation.clear_tvstation(db)

    elif args.action == "backfillgenres":
        if not args.tmdbApiKey:
            print("ERROR: --key is required for backfillgenres")
            sys.exit(2)
        limit_str = f", limit {args.limit}" if args.limit else ""
        verbose(f"Backfilling genres from TMDB{limit_str}")
        movie, _ = online.initialize_tmdb(args.tmdbApiKey)
        database.scanGenres(db, movie, limit=args.limit)

    elif args.action == "refreshmovie":
        if not args.tmdbApiKey:
            print("ERROR: --key is required for refreshmovie")
            sys.exit(2)
        movie, _ = online.initialize_tmdb(args.tmdbApiKey)
        if args.tmdbId:
            verbose(f"Refreshing movie TMDB ID {args.tmdbId}")
            database.refresh_movie(db, movie, args.tmdbId)
        else:
            verbose("Bulk refresh: top-10 by score + 10 random + 10 oldest-refreshed")
            database.refresh_movies_bulk(db, movie)

    elif args.action == "resetcounters":
        verbose("Resetting cast/genre error counters")
        database.reset_error_counters(db)

    elif args.action == "setcollectionregex":
        if not args.collection:
            print("ERROR: --collection is required for setcollectionregex")
            sys.exit(2)
        if not args.movieRegex and not args.tvshowRegex:
            print("ERROR: at least one of --movie-regex or --tvshow-regex is required")
            sys.exit(2)
        if args.movieRegex:
            try:
                p = re.compile(args.movieRegex)
            except re.error as e:
                print(f"ERROR: --movie-regex is invalid: {e}")
                sys.exit(2)
            missing = [g for g in ('name', 'year') if g not in p.groupindex]
            if missing:
                print(f"ERROR: --movie-regex missing required named groups: {', '.join(missing)}")
                sys.exit(2)
        if args.tvshowRegex:
            try:
                p = re.compile(args.tvshowRegex)
            except re.error as e:
                print(f"ERROR: --tvshow-regex is invalid: {e}")
                sys.exit(2)
            missing = [g for g in ('name', 'year', 'season', 'episode') if g not in p.groupindex]
            if missing:
                print(f"ERROR: --tvshow-regex missing required named groups: {', '.join(missing)}")
                sys.exit(2)
        col_id, created = database.create_or_get_collection(db, args.collection)
        if created:
            verbose(f"Created collection '{args.collection}'")
        database.set_collection_regex(db, args.collection, args.movieRegex, args.tvshowRegex)
        verbose(f"Regex updated for collection '{args.collection}'")

    elif args.action == "clearscreenshots":
        verbose("Clearing all screenshots")
        database.clear_screenshots(db)
    elif args.action == "getscreenshots":
        if not args.libPath:
            print("ERROR: --path is required for getscreenshots")
            sys.exit(2)
        if not args.collection:
            print("ERROR: --collection is required for getscreenshots")
            sys.exit(2)
        verbose(f"Capturing screenshots for collection '{args.collection}' from '{args.libPath}'")
        files.backfill_screenshots(db, args.collection, args.libPath)

    else:
        print("ERROR: no or unknown action specified")
        sys.exit(2)


def tagging(args, remaining=None):
    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = database.initialize_db(args.dbfile)

    if args.action == "list":
        tags.list(db)
    elif args.action == "export":
        tags.export(db, args.dbfile)
    elif args.action == "add":
        if args.tag is None or args.regex is None:
            print("ERROR: missing tag or regex")
            sys.exit(2)
        else:
            try:
                re.compile(args.regex)
            except re.error:
                print("ERROR: regex invalid")
                sys.exit(2)
        tags.add(db, args.tag, args.regex)
    elif args.action == "delete":
        if args.allTags:
            tags.delete_all(db)
        else:
            tags.delete(db, args.tag, args.regex)
    else:
        print("ERROR: no or unknown action specified")
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(prog="tvthekidx", description="tvthek index")
    parser.add_argument("--quiet", "-q", action="store_true", dest="quiet", help="quiet (set verbose to 0)")
    parser.add_argument("--verbose", "-v", action="count", dest="verbose", default=0, help="verbosity level")

    subparsers = parser.add_subparsers()
    subparsers.required = True

    indexerparser = subparsers.add_parser("index", help="create and maintain the tvthekidx database")
    indexerparser.set_defaults(func=indexer)
    indexerparser.add_argument("--database", "-d", action="store", dest="dbfile", default="tvthek.db", help="TVthekIdx database")
    indexerparser.add_argument("--path", "-p", action="store", dest="libPath", help="path to scan", required=True)
    indexerparser.add_argument("--type", "-t", action="store", dest="libType", default="movies", help="type of content")
    indexerparser.add_argument("--key", "-k", action="store", dest="tmdbApiKey", help="TMDB API key", required=True)
    indexerparser.add_argument("--collection", "-c", action="store", dest="collection", default="TVthek", help="collection name")
    indexerparser.add_argument("--recursive", "-r", action="store_true", dest="recursiveSearch", help="recursive search")

    exporterparser = subparsers.add_parser("export", help="export tvthekidx content")
    exporterparser.set_defaults(func=exporter)
    exporterparser.add_argument("--database", "-d", action="store", dest="dbfile", default="tvthek.db", help="TVthekIdx database")
    exporterparser.add_argument("--collection", "-c", action="store", dest="collectionStr", default=None, help="comma-separated list of collections")
    exporterparser.add_argument("--format", "-f", action="store", dest="format", default="html", help="export plugin name")

    maintenanceparser = subparsers.add_parser("maintenance", help="database and inference maintenance")
    maintenanceparser.set_defaults(func=maintenance)
    maintenanceparser.add_argument("--database", "-d", action="store", dest="dbfile", default="tvthek.db", help="TVthekIdx database")
    maintenanceparser.add_argument("--action", "-a", action="store", dest="action", default=None, help="createdb/compressdb/upgradedb/detecttvstations/cleartvstations/clearscreenshots/getscreenshots/backfillgenres/refreshmovie/resetcounters/setcollectionregex")
    maintenanceparser.add_argument("--path", "-p", action="store", dest="libPath", default=None, help="path to video files (required for getscreenshots)")
    maintenanceparser.add_argument("--collection", "-c", action="store", dest="collection", default=None, help="collection filter (optional for getscreenshots)")
    maintenanceparser.add_argument("--key", "-k", action="store", dest="tmdbApiKey", default=None, help="TMDB API key (required for refreshmovie/backfillgenres)")
    maintenanceparser.add_argument("--tmdb-id", action="store", dest="tmdbId", type=int, default=None, help="TMDB movie ID (optional for refreshmovie; omit to refresh top/random/oldest batch)")
    maintenanceparser.add_argument("--limit", "-l", action="store", dest="limit", type=int, default=None, help="max movies to process per run (for backfillgenres)")
    maintenanceparser.add_argument("--movie-regex", action="store", dest="movieRegex", default=None, help="movie filename regex with named groups (?P<name>, ?P<year>); for setcollectionregex")
    maintenanceparser.add_argument("--tvshow-regex", action="store", dest="tvshowRegex", default=None, help="tvshow filename regex with named groups (?P<name>, ?P<year>, ?P<season>, ?P<episode>); for setcollectionregex")

    tagsparser = subparsers.add_parser("tags", help="file tagging")
    tagsparser.set_defaults(func=tagging)
    tagsparser.add_argument("--database", "-d", action="store", dest="dbfile", default="tvthek.db", help="TVthekIdx database")
    tagsparser.add_argument("--action", "-a", action="store", dest="action", default=None, help="list/add/delete/export")
    tagsparser.add_argument("--tag", "-t", action="store", dest="tag", default=None, help="tag")
    tagsparser.add_argument("--regex", "-r", action="store", dest="regex", default=None, help="regular expression")
    tagsparser.add_argument("--all", action="store_true", dest="allTags", help="delete all tags (requires --action delete)")

    args, remaining = parser.parse_known_args()

    if args.quiet:
        setVerbosity(0)
    else:
        verbose("TVThe(k)Idx version " + __version__)
        setVerbosity(args.verbose + 1)
        verbose("Verbosity level: " + str(getVerbosity()), 2)

    args.func(args, remaining)
