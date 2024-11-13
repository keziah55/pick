#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add series to DB.
"""
from pathlib import Path
from collections import Counter
import warnings

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from mediabrowser.models import BaseVisionItem, VisionItem
from populate_db import ProgressBar


def write_series_to_db(csv_file: Path, csv_sep="\t"):
    header, *rows = [line.split(csv_sep) for line in csv_file.read_text().split("\n") if line]

    for row in rows:
        name, search_str, pks, description, img = row

        if pks:
            members = [VisionItem.objects.get(pk=int(pk)) for pk in pks.split(",")]
        else:
            if not search_str:
                search_str = name
            members = list(VisionItem.objects.filter(title__icontains=search_str))

        if len(members):
            warnings.warn(f"Could not find VisionItems for {name=}")
            continue

        if not img:
            img = members[0].img

        years = []
        counts = {key: Counter() for key in ["director", "stars", "genres", "keywords"]}

        for member in members:
            if len(years) == 0:
                years = [member.year] * 2
            else:
                if member.year < years[0]:
                    years[0] = member.year
                elif member.year > years[1]:
                    years[1] = member.year

            for name, counter in counts.items():
                obj = getattr(member, name)
                counter.update([o.pk for o in obj.all()])
                # data_set.union(set([o.pk for o in obj.all()]))

        year, alt_year = years

        item = BaseVisionItem(
            title=name,
            img=img,
            media_type=BaseVisionItem.SERIES,
            year=year,
            alt_year=alt_year,
            description=description,
        )
        item.save()
        
        for name, counter in counts.items():
            attr = getattr(item, name)
            for pk in [c[0] for c in counter.most_common()]:
                pass



if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="media series csv file")

    args = parser.parse_args()

    write_series_to_db(Path(args.file))
