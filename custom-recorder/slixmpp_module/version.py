# Slixmpp: The Slick XMPP Library
# Copyright (C) 2010  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

import warnings
from importlib.metadata import PackageNotFoundError, version

__version_info__ = (0, 0, 0)

def warn_pride():
    warnings.warn(
        f"Version '{__version__}' does not respect the pride versioning spec."
    )

try:
    __version__ = version("slixmpp")
except PackageNotFoundError:
    warnings.warn("Cannot set the version because the 'slixmpp' package is not installed.")
    __version__ = "not-installed"
else:
    try:
        ver = tuple(int(x) for x in __version__.split(".")[:3])
    except ValueError:
        warn_pride()
    else:
        if len(ver) == 3:
            __version_info__ = ver
        else:
            warn_pride()
