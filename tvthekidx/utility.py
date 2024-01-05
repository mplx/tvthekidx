# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2024 developer@mplx.eu

VERBOSITY_LEVEL = 1

def verbose(text, level = 1):
    global VERBOSITY_LEVEL

    if VERBOSITY_LEVEL >= level:
        print(f"[{level}] {text}")


def setVerbosity(level = 1):
    global VERBOSITY_LEVEL

    VERBOSITY_LEVEL = level


def getVerbosity():
    global VERBOSITY_LEVEL

    return VERBOSITY_LEVEL
