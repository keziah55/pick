#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for creating and updating database entries for all films in a list of filenames.
"""

from pathlib import Path
from datetime import timedelta

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from mediabrowser.models import VisionItem, VisionSeries
from populate_db import PopulateDatabase, StdoutWriter, HtmlWriter
from populate_db.logger import timestamp


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-f", "--films", help="Path to films text file")
    parser.add_argument("-p", "--patch", help="Path to patch csv")
    parser.add_argument("-m", "--physical-media", help="Path to physical media csv")
    parser.add_argument("-a", "--aliases", help="Path to aliases csv")
    parser.add_argument("-s", "--series", help="Path to series csv")
    parser.add_argument("-d", "--descriptions", help="Path to csv file of descriptions")
    parser.add_argument(
        "-c", "--clear", help="Clear VisionItems and VisionSeries", action="store_true"
    )
    parser.add_argument("-q", "--quiet", help="Don't write anything to stdout", action="store_true")
    parser.add_argument(
        "-v", "--verbose", help="Print list of new VisionItems", action="store_true"
    )
    parser.add_argument("--html", help="If provided, write to [html]/index.html instead of stdout")

    args = parser.parse_args()

    files = {
        "films": args.films,
        "patch": args.patch,
        "physical_media": args.physical_media,
        "aliases": args.aliases,
        "series": args.series,
        "descriptions": args.descriptions,
    }
    for key, value in files.items():
        if value is not None:
            p = files[key] = Path(value)
            if not p.exists():
                raise FileNotFoundError(f"'{key}' file '{p}' does not exist.")

    if args.html:
        writer = HtmlWriter(quiet=args.quiet, out_dir=Path(args.html))
    else:
        writer = StdoutWriter(quiet=args.quiet)

    pop_db = PopulateDatabase(
        quiet=args.quiet,
        physical_media=files["physical_media"],
        alias_csv=files["aliases"],
        writer=writer,
    )

    if args.clear:
        pop_db.clear(VisionItem)
        pop_db.clear(VisionSeries)

    if args.films or args.patch:

        t0 = timestamp()
        writer.write(f"{t0}")
        writer.write("Populating items...")
        pop_db.populate_items(files["films"], files["patch"], description_csv=files["descriptions"])

        if not args.quiet:
            indent = "  "

            t = timestamp() - t0
            writer.write(f"Completed in {t}")

            writer.write("\nBreakdown:")
            writer.write(f"Getting data from IMDb took {timedelta(seconds=pop_db._imdb_time)}")
            writer.write(f"Writing data to DB took     {timedelta(seconds=pop_db._db_time)}")

            writer.write("Created models in DB:")
            for k, v in pop_db._created_item_count.items():
                writer.write(f"{indent}{k}: {v}")

            if args.verbose:
                writer.write("\nCreated VisionItems:")
                for name in pop_db._created_visionitems:
                    writer.write(f"{indent}{name}")

            writer.write("\n")

    if args.series:
        writer.write(f"{t0}")
        writer.write("Populating series...")

        t1 = timestamp()
        n = pop_db.populate_series(files["series"])

        t = timestamp() - t0
        writer.write(f"Completed in {t}")
        writer.write(f"\nCreated {n} series in DB")
