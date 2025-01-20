#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 15:37:30 2025

@author: keziah
"""
from pathlib import Path
from typing import Optional

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from mediabrowser.models import MediaItem, VisionItem, VisionSeries
from django.core.exceptions import ObjectDoesNotExist


def make_series(
    item_pks: list[int],
    title: str,
    description: Optional[str] = None,
) -> VisionSeries:

    items = [MediaItem.objects.get(pk=pk) for pk in item_pks]
    derived_items = []

    filename = ""
    img = items[0].img
    media_type = MediaItem.SERIES

    year = [None, None]
    runtime = [None, None]
    user_rating = 0
    imdb_rating = 0

    director = []
    stars = []
    genre = []
    keyword = []

    description = description if description is not None else title

    for item in items:

        item = _get_dervied_instance(item)
        derived_items.append(item)

        if isinstance(item, VisionSeries):
            year_max_attr = "year_max"
            runtime_max_attr = "runtime_max"

        else:
            year_max_attr = "year"
            runtime_max_attr = "runtime"

        if year[0] is None or item.year < year[0]:
            year[0] = item.year

        if year[1] is None or getattr(item, year_max_attr) > year[1]:
            year[1] = getattr(item, year_max_attr)

        if runtime[0] is None or item.runtime < runtime[0]:
            runtime[0] = item.runtime

        if runtime[1] is None or getattr(item, runtime_max_attr) > runtime[1]:
            runtime[1] = getattr(item, runtime_max_attr)

        user_rating += item.user_rating
        imdb_rating += item.imdb_rating

        director += list(item.director.all())
        stars += list(item.stars.all())
        genre += list(item.genre.all())
        keyword += list(item.keywords.all())

    # get unique values from lists, ordered by number of occurrences
    for lst in [director, stars, genre, keyword]:
        lst = list(dict.fromkeys(sorted(lst, key=lst.count, reverse=True)))

    user_rating = round(user_rating / len(items))
    imdb_rating = imdb_rating / len(items)

    series = VisionSeries(
        title=title,
        filename=filename,
        year=year[0],
        year_max=year[1],
        runtime=runtime[0],
        runtime_max=runtime[1],
        img=img,
        media_type=media_type,
        description=description,
        alt_description="",
        user_rating=user_rating,
        imdb_rating=imdb_rating,
    )

    series.save()
    print(f"created series {series}")

    for person in director:
        series.director.add(person)

    for person in stars:
        series.stars.add(person)

    for g in genre:
        series.genre.add(g)

    for kw in keyword:
        series.keywords.add(kw)

    for item in derived_items:
        series.members.add(item)
        item.parent_series.add(series)
        item.save()

    series.save()
    print(f"updated series {series}")

    return series


def _get_dervied_instance(item):
    try:
        item = VisionSeries.objects.get(pk=item.pk)
    except ObjectDoesNotExist:
        try:
            item = VisionItem.objects.get(pk=item.pk)
        except ObjectDoesNotExist:
            msg = f"Item {item.pk} {item} is neither a VisionSeries nor a VisionItem."
            raise RuntimeError(msg)
    return item


if __name__ == "__main__":

    series = []
    data = [
        ((2, 3, 1), "Before trilogy"),
        ((9, 7, 8), "Men in Black"),
    ]
    for item_pks, title in data:
        srs = make_series(item_pks, title)
        series.append(srs)

    make_series([srs.pk for srs in series], "All Series")

    # for series in VisionSeries.objects.all():
    #     members = [VisionItem.objects.get(pk=item.pk) for item in series.members.all()]
