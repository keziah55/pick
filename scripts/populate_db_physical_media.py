#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  6 21:31:01 2023

@author: keziah
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

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from populate_db import PopulateDatabase
from mediabrowser.models import VisionItem


def populate_physical(not_in_db_file, patch_csv, media_csv):

    # read list of films (just film names from physical media list)
    with open(not_in_db_file) as fileobj:
        text = fileobj.read()
    films = [Path(s) for s in text.split("\n") if s]

    # make patch dict
    patch = PopulateDatabase._read_patch_csv(patch_csv)

    # make PopulateDatabase instance
    pop_db = PopulateDatabase(physical_media=media_csv)

    pop_db.digital_default = False

    # populate
    pop_db._populate(films, patch)


def make_films_list(media_csv, out_path):
    physical_media = PopulateDatabase._read_physical_media_csv(media_csv)
    out_path = Path(out_path)

    not_in_db = []
    in_db = []

    for title, disc_index in physical_media.items():
        if any(s in title for s in ["bonus features", "special features", "extras", "disc 2"]):
            continue

        item_info = "\t".join([disc_index, title])

        try:
            VisionItem.objects.get(disc_index__exact=disc_index)
        except ObjectDoesNotExist:
            not_in_db.append(item_info)
        except MultipleObjectsReturned:
            print(f"Multiple items found for {disc_index=}, '{title}'")
        else:
            in_db.append(item_info)

    fnames = {
        "not_in_db": not_in_db,
        "in_db": in_db,
    }

    for fname, lst in fnames.items():
        with open(out_path.joinpath(f"{fname}.csv"), "w") as fileobj:
            fileobj.write("\n".join(lst))

    print(f"{len(not_in_db)} items to add to DB; {len(in_db)} items already in DB")


def check_physical(in_db_file):
    with open(in_db_file) as fileobj:
        text = fileobj.read()
    # in_db = [s for s in text.split("\n") if s]
    in_db = dict([line.split("\t") for line in text.split("\n") if line])

    # print(in_db[157])
    # in_db = in_db[183:]

    # qs = VisionItem.objects.filter(physical=True)
    # db_titles = [item.title for item in qs]

    for disc_index, title in in_db.items():
        items = VisionItem.objects.filter(title__icontains=title)
        if len(items) == 0:
            print(f"None found for {title}")
            continue
        elif len(items) > 1:
            msg = f"\nmultiple found for {title}:\n"
            for i, item in enumerate(items):
                msg += f"  {i} {item.title}\n"
            msg += "Select index: "
            idx = input(msg)
            idx = int(idx)
        else:
            idx = 0
        item = items[idx]
        if item.physical and item.disc_index == disc_index:
            continue

        item.physical = True
        item.disc_index = disc_index
        item.save()

        # msg = (
        #     f"{item.title} available physically at index {disc_index}\n"
        #     f"In DB    : physical={item.physical}, disc_index={item.disc_index}\n"
        #     f"Change to: physical=True, {disc_index=} [Y/n]?\n"
        # )
        # change = input(msg).lower().strip()
        # if not change or change == "y":
        #     item.physical = True
        #     item.disc_index = disc_index
        #     item.save()
        # elif change == "n":
        #     item.physical = False
        #     item.disc_index = ""
        #     item.save()


def update_not_in_db(not_in_db_file):
    """Ask for pk for films."""

    with open(not_in_db_file) as fileobj:
        text = fileobj.read()
    not_in_db = dict([line.split("\t") for line in text.split("\n") if line])

    for disc_index, title in not_in_db.items():
        msg = f"\n'{title}' not found in DB. Set primary key: "
        pk = input(msg).strip()
        if pk == "":
            continue

        item = VisionItem.objects.get(pk=int(pk))

        item.physical = True
        item.disc_index = disc_index
        item.save()


if __name__ == "__main__":

    import argparse

    # parser = argparse.ArgumentParser(description=__doc__)

    # parser.add_argument("-f", "--films", help="Path to films not in DB text file")
    # parser.add_argument("-p", "--patch", help="Path to patch csv")
    # parser.add_argument("-m", "--physical-media", help="Path to physical media csv")

    # args = parser.parse_args()

    # populate_physical(args.films, args.patch, args.physical_media)

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--physical-media", help="Path to physical media csv")
    parser.add_argument("-o", "--out-path", help="Path to write to")
    parser.add_argument("-f", "--file")

    args = parser.parse_args()

    make_films_list(args.physical_media, args.out_path)

    # check_physical(args.file)
    # update_not_in_db(args.file)
