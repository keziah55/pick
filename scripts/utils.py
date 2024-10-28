#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions and imports that may be useful in an interactive session.
"""

from mediabrowser.models import VisionItem, Genre, Keyword, Person


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


__all__ = ["VisionItem", "Genre", "Keyword", "Person", "search_items"]
