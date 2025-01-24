#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add series to DB.
"""
from pathlib import Path
import warnings
from typing import Union, Optional

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from django.core.exceptions import ObjectDoesNotExist
from mediabrowser.models import VisionItem, VisionSeries, MediaItem
from populate_db import ProgressBar


def write_series_to_db(csv_file: Path, csv_sep="\t", sort_by_year=True):
    header, *rows = [line.split(csv_sep) for line in csv_file.read_text().split("\n") if line]

    progress = ProgressBar(len(rows))

    for n, row in enumerate(rows):
        name, search_str, pks, description, img = row

        if pks:
            members = [_get_item(pk) for pk in pks.split(",")]
        else:
            if not search_str:
                search_str = name
            members = list(VisionItem.objects.filter(title__icontains=search_str))
            members += list(VisionSeries.objects.filter(title__icontains=search_str))

            # sort in chronological order
            if sort_by_year:
                members.sort(key=lambda item: item.year)

        if len(members) == 0:
            warnings.warn(f"Could not find VisionItem/VisionSeries for {name=}")
        else:
            make_series(members, name)

        progress.progress(n + 1)


def make_series(
    items: list[Union[VisionItem, VisionSeries]],
    title: str,
    description: Optional[str] = None,
) -> VisionSeries:

    # items = [MediaItem.objects.get(pk=pk) for pk in item_pks]
    derived_items = []

    filename = ""
    img = items[0].img
    media_type = MediaItem.SERIES

    year = [None, None]
    runtime = [None, None]
    user_rating = 0
    imdb_rating = 0

    refs = {
        "director": [],
        "stars": [],
        "genre": [],
        "keyword": [],
    }

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

        # user_rating += item.user_rating
        user_rating = max(item.user_rating, user_rating)
        imdb_rating += item.imdb_rating

        refs["director"] += list(item.director.all())
        refs["stars"] += list(item.stars.all())
        refs["genre"] += list(item.genre.all())
        refs["keyword"] += list(item.keywords.all())

    # get unique values from lists, ordered by number of occurrences
    for key, lst in refs.items():
        refs[key] = list(dict.fromkeys(sorted(lst, key=lst.count, reverse=True)))

    # user_rating = round(user_rating / len(items))
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

    for person in refs["director"]:
        series.director.add(person)

    for person in refs["stars"]:
        series.stars.add(person)

    for g in refs["genre"]:
        series.genre.add(g)

    for kw in refs["keyword"]:
        series.keywords.add(kw)

    for item in derived_items:
        series.members.add(item)
        item.parent_series = series
        item.save()

    series.save()

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


def _get_item(pk):
    try:
        item = VisionItem.objects.get(pk=pk)
    except ObjectDoesNotExist:
        try:
            item = VisionSeries.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise ValueError(f"No VisionItem or VisionSeries found for {pk}")
    return item


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="media series csv file")

    args = parser.parse_args()

    write_series_to_db(Path(args.file))
