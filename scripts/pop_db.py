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
from populate_db import PopulateDatabase, StdoutWriter, HtmlWriter


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
    parser.add_argument("--html", help="If provided, write to [html]/index.html instead of stdout")

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

        t0 = time.monotonic()
        writer.write("Populating items...")
        pop_db.update(files["films"], files["patch"])

        if not args.quiet:
            indent = "  "

            t = time.monotonic() - t0
            s = format_time(t)
            writer.write(f"Completed in {s}")

            writer.write("\nBreakdown:")
            writer.write(f"Getting data from IMDb took {format_time(pop_db._imdb_time)}")
            writer.write(f"Writing data to DB took     {format_time(pop_db._db_time)}")

            writer.write("Created models in DB:")
            s = "\n".join([f"{indent}{k}: {v}" for k, v in pop_db._created_item_count.items()])
            writer.write(s)

            if args.verbose:
                writer.write("\nCreated VisionItems:")
                s = "\n".join([f"{indent}{name}" for name in pop_db._created_visionitems])
                writer.write(s)

            writer.write("\n")

    if args.series:
        writer.write("Populating series...")

        t1 = time.monotonic()
        n = pop_db.write_series_to_db(files["series"])

        s = format_time(t)
        writer.write(f"Completed in {s}")
        writer.write(f"\nCreated {n} series in DB")
