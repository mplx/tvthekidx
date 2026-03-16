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

    db = database.initialize_db(args.dbfile)
    movie, search = online.initialize_tmdb(args.tmdbApiKey)

    files.scanDir(db, args.collection, args.libPath, args.recursiveSearch)
    database.scanMovies(db, search)
    database.scanCredits(db, movie)


def exporter(args, remaining):
    collection = args.collectionStr.split(",") if args.collectionStr else None

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = database.create_connection(args.dbfile)
    plugin = export.load_exporter(args.format)
    plugin_args = plugin.parse_args(remaining)
    plugin.export(db, collection, args, plugin_args)


def maintenance(args, remaining=None):
    if args.action == "createdb":
        if os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' already exists")
            sys.exit(2)
        database.initialize_db(args.dbfile)
    elif args.action == "compressdb":
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        db = database.create_connection(args.dbfile)
        database.cleanup_db(db)
    elif args.action == "upgradedb":
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        database.upgrade_db(args.dbfile)
    elif args.action == "detecttvstations":
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        from . import tvstation
        model = tvstation.load_model()
        if model is None:
            print("ERROR: model file 'best.pt' not found")
            sys.exit(2)
        db = database.create_connection(args.dbfile)
        tvstation.backfill_tvstation(db, model)
    elif args.action == "cleartvstations":
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        db = database.create_connection(args.dbfile)
        from . import tvstation
        tvstation.clear_tvstation(db)
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
                recompiled = re.compile(args.regex)
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
    maintenanceparser.add_argument("--action", "-a", action="store", dest="action", default=None, help="createdb/compressdb/upgradedb/detecttvstations/cleartvstations")

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
