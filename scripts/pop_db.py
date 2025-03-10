#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
For creating and updating database entries for all films in a list of filenames.

Either import `PopulateDatabase` class or run as script. In the latter case,
see `populate_db.py -h` for options.
"""

from pathlib import Path
import time

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from mediabrowser.models import VisionItem, VisionSeries
from populate_db import PopulateDatabase


if __name__ == "__main__":

    def format_time(t):
        # take t in seconds, return string
        t /= 60
        hours, minssecs = divmod(t, 60)
        mins, secs = divmod((minssecs * 60), 60)
        if hours > 0:
            s = f"{hours:02.0f}h{mins:02.0f}m{secs:02.0f}s"
        else:
            s = f"{mins:02.0f}m{secs:02.0f}s"
        return s

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-f", "--films", help="Path to films text file")
    parser.add_argument("-p", "--patch", help="Path to patch csv")
    parser.add_argument("-m", "--physical-media", help="Path to physical media csv")
    parser.add_argument("-a", "--aliases", help="Path to aliases csv")
    parser.add_argument("-s", "--series", help="Path to series csv")
    parser.add_argument(
        "-c", "--clear", help="Clear VisionItems and VisionSeries", action="store_true"
    )
    parser.add_argument("-q", "--quiet", help="Don't write anything to stdout", action="store_true")
    parser.add_argument(
        "-v", "--verbose", help="Print list of new VisionItems", action="store_true"
    )

    args = parser.parse_args()

    files = {
        "films": args.films,
        "patch": args.patch,
        "physical_media": args.physical_media,
        "aliases": args.aliases,
        "series": args.series,
    }
    for key, value in files.items():
        if value is not None:
            p = files[key] = Path(value)
            if not p.exists():
                raise FileNotFoundError(f"'{key}' file '{p}' does not exist.")

    if any([args.films, args.patch, args.clear]):

        t0 = time.monotonic()

        pop_db = PopulateDatabase(
            quiet=args.quiet, physical_media=files["physical_media"], alias_csv=files["aliases"]
        )

        if args.clear:
            pop_db.clear(VisionItem)
            pop_db.clear(VisionSeries)

        if not args.quiet:
            print("Populating items...")

        pop_db.update(files["films"], files["patch"])

        if not args.quiet:
            indent = "  "

            t = time.monotonic() - t0
            s = format_time(t)
            print(f"Completed in {s}")

            print("\nBreakdown:")
            print(f"Getting data from IMDb took {format_time(pop_db._imdb_time)}")
            print(f"Writing data to DB took     {format_time(pop_db._db_time)}")

            print("Created models in DB:")
            s = "\n".join([f"{indent}{k}: {v}" for k, v in pop_db._created_item_count.items()])
            print(s)

            if args.verbose:
                print("\nCreated VisionItems:")
                s = "\n".join([f"{indent}{name}" for name in pop_db._created_visionitems])
                print(s)

            print()

    if args.series:
        if not args.quiet:
            print("Populating series...")

        t1 = time.monotonic()
        n = pop_db.write_series_to_db(files["series"], quiet=args.quiet)

        if not args.quiet:
            s = format_time(t)
            print(f"Completed in {s}")
            print(f"\nCreated {n} series in DB")
