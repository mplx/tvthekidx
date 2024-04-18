#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2024 developer@mplx.eu

from . import files
from . import online
from . import database
from . import htmlexport
from . utility import verbose, getVerbosity, setVerbosity
from . _version import __version__

import os
import sys
import argparse


def indexer(args):
    if args.libType != "movies":
        print("ERROR: currently only type 'movies' supported (tvshows require a different TMDB API)")
        sys.exit(2)

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = database.initialize_db(args.dbfile)
    movie, search = online.initialize_tmdb(args.tmdbApiKey)

    files.scanDir(db, args.collection, args.libPath, args.recursiveSearch)
    database.scanMovies(db, search)
    database.scanCredits(db, movie)


def exporter(args):
    collection = None
    if args.collectionStr:
        collection = args.collectionStr.split(",")

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = database.create_connection(args.dbfile)
    with open(args.outputFile, 'w', encoding='utf8') as f:
        verbose(f"Exporting to {args.outputFile}...", 1)
        htmlexport.writeHeader(f, args.title)
        if not args.skipHeader:
            htmlexport.writeMoviesImageTitle(db, f, collection)
        htmlexport.writeMoviesDetail(db, f, collection, args.targetURL)
        if not args.skipActors:
            htmlexport.writeActorsDetail(db, f, collection)
        htmlexport.writeFooter(f)


def dbtools(args):
    if args.action == 'create':
        if os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' already exists")
            sys.exit(2)
        database.initialize_db(args.dbfile)
    elif args.action == 'compress':
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        db = database.create_connection(args.dbfile)
        database.cleanup_db(db)
    elif args.action == 'upgrade':
        if not os.path.isfile(args.dbfile):
            print(f"ERROR: database '{args.dbfile}' not found")
            sys.exit(2)
        database.upgrade_db(args.dbfile)
    else:
        print("ERROR: no or unknown action specified")
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(prog='tvthekidx', description='tvthek index')
    parser.add_argument('--quiet', '-q', action='store_true', dest='quiet', help='quiet (set verbose to 0)')
    parser.add_argument('--verbose', '-v', action='count', dest='verbose', default=0, help='verbosity level')

    subparsers = parser.add_subparsers()
    subparsers.required = True

    indexerparser = subparsers.add_parser('index', help='create and maintain the tvthekidx database')
    indexerparser.set_defaults(func=indexer)
    indexerparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    indexerparser.add_argument('--path', '-p', action='store', dest='libPath', help='path to scan', required=True)
    indexerparser.add_argument('--type', '-t', action='store', dest='libType', default='movies', help='type of content')
    indexerparser.add_argument('--key', '-k', action='store', dest='tmdbApiKey', help='TMDB API key', required=True)
    indexerparser.add_argument('--collection', '-c', action='store', dest='collection', default='TVthek', help='collection name')
    indexerparser.add_argument('--recursive', '-r', action='store_true', dest='recursiveSearch', help='recursive search')

    exporterparser = subparsers.add_parser('export', help='export tvthekidx content')
    exporterparser.set_defaults(func=exporter)
    exporterparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    exporterparser.add_argument('--title', '-t', action='store', dest='title', default='TVThek Index', help='page title')
    exporterparser.add_argument('--output', '-o', action='store', dest='outputFile', default='tvthek.html', help='oputput file')
    exporterparser.add_argument('--collection', '-c', action='store', dest='collectionStr', default=None, help='comma-separated list of collections')
    exporterparser.add_argument('--skip-actors', action='store_true', dest='skipActors', help='do not include actors section')
    exporterparser.add_argument('--skip-header', action='store_true', dest='skipHeader', help='do not include header with top and new sections')
    exporterparser.add_argument('--url', action='store', dest='targetURL', default='./', help='video hyperlink prefix')

    exporterparser = subparsers.add_parser('database', help='database tools')
    exporterparser.set_defaults(func=dbtools)
    exporterparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    exporterparser.add_argument('--action', '-a', action='store', dest='action', default=None, help='create/compress/upgrade')

    args = parser.parse_args()

    if args.quiet:
        setVerbosity(0)
    else:
        verbose("TVThe(k)Idx version " + __version__)
        setVerbosity(args.verbose + 1)
        verbose("Verbosity level: " + str(getVerbosity()), 2)

    args.func(args)
