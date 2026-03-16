# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import importlib
import sys


def load_exporter(format_name):
    module_name = f"{__package__}.export_{format_name}"
    try:
        return importlib.import_module(module_name)
    except ImportError:
        print(f"ERROR: exporter '{format_name}' not found (expected module tvthekidx.export_{format_name})")
        sys.exit(2)
