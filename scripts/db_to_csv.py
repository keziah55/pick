#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write all VisionItem data to csv.
"""

from pathlib import Path

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from mediabrowser.models import VisionItem


def write_db_to_csv(csv_file: Path, csv_sep: str = "\t", line_sep: str = "\n"):

    fields = [
        "filename",
        "title",
        "year",
        # "img",
        "local_img",
        "media_type",
        # "children",
        # "runtime",
        "imdb_id",
        # "language",
        "colour",
        "alt_title",
        # "director",
        # "stars",
        # "genre",
        # "keywords",
        # "description",
        "alt_description",
        "alt_versions",
        "is_alt_version",
        # "imdb_rating",
        "user_rating",
        "bonus_features",
        "digital",
        "physical",
        "disc_index",
    ]

    rows = [csv_sep.join(fields)]

    for item in VisionItem.objects.filter(title__icontains="before"): #.all():
        row = []
        for field in fields:
            value = getattr(item, field)
            # if field in "local_img":
            #     value = str(value)
            if field == "alt_versions":
                value = ",".join([item.filename for item in value.all()])
            elif field == "disc_index" and value != "":
                case, slot = [int(s) for s in value.split(".")]
                value = f"{case}.{slot:03d}"

            value = str(value)

            if field in ["title", "alt_title"] and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            row.append(value)
        row = csv_sep.join(row)
        rows.append(row)

    with open(csv_file, "w") as fileobj:
        fileobj.write(line_sep.join(rows))


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="csv file to write to")
    args = parser.parse_args()

    write_db_to_csv(Path(args.file))
