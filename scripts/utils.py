#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions and imports that may be useful in an interactive session.
"""

from pathlib import Path
import sys
import os
from mediabrowser.models import VisionItem, Genre, Keyword, Person, MediaItem, VisionSeries


def search_items(s: str):
    """
    Search for `VisionItems` where title contains `s`.

    Prints title, year and primary key are all matching objects, and returns query set.

    Parameters
    ----------
    s : str
        String to search for in `VisionItem` titles. Not case sensitive.

    Returns
    -------
    items : QuerySet
        Set of items matching `s`.

    """
    items = VisionItem.objects.filter(title__icontains=s)
    for item in items:
        print(item, item.pk)
    return items


def setup_django():
    """Set paths, import django and call `django.setup()`."""
    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()


__all__ = [
    "VisionItem",
    "Genre",
    "Keyword",
    "Person",
    "MediaItem",
    "search_items",
    "VisionSeries",
    "setup_django",
]
