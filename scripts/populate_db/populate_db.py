#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
For creating and updating database entries for all films in a list of filenames.

Either import `PopulateDatabase` class or run as script. In the latter case,
see `populate_db.py -h` for options.
"""

from pathlib import Path
import warnings
import time
import logging
from typing import Any

from .read_data_files import item_patch_equal, make_combined_dict
from .progress_bar import ProgressBar
from .person_info import PersonInfo
from .media_info import MediaInfoProcessor, MediaInfo

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    import os

    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from mediabrowser.models import VisionItem, VisionSeries, Genre, Keyword, Person


ts = time.strftime("%Y-%m-%d-%H:%M:%S")
logger = logging.getLogger("populate_db")


class PopulateDatabase:
    """Class to create records in database from list of file names and/or csv file."""

    field_map = {
        "genre": Genre,
        "keywords": Keyword,
        ("director", "stars"): Person,
    }

    def __init__(self, quiet=False, physical_media=None, database="default"):

        self._created_item_count = {"visionitem": 0, "genre": 0, "keywords": 0, "person": 0}
        self._created_visionitems = []
        self._imdb_time = 0
        self._db_time = 0

        self._quiet = quiet

        self._database = database

        self._media_info_processor = MediaInfoProcessor(physical_media)

        self._direct_fields = []
        self._ref_fields = []

        for field in VisionItem._meta.get_fields():
            if field.name == "id":
                continue
            if isinstance(field, (models.ManyToManyField, models.ForeignKey)):
                self._ref_fields.append(field.name)
            else:
                self._direct_fields.append(field.name)

        self._waiting_for_alt_versions: list[tuple[VisionItem, str]] = []

        logging.basicConfig(
            filename=f"populate_db-{ts}.log",
            level=logging.INFO,
            format="%(levelname)s: %(name)s: %(asctime)s: %(message)s",
        )

    def _write(self, s):
        if not self._quiet:
            print(s)

    def _add_to_db(self, filename, media_info):
        """
        Create a `VisionItem` in the database for `media_info`

        Parameters
        ----------
        filename : str
            File name of film
        media_info : MediaInfo
            Dataclass with info

        Returns
        -------
        item : VisionItem
            VisionItem added to database.
        """
        t0 = time.monotonic()

        item = VisionItem(
            title=media_info.title,
            filename=filename,
            img=media_info.image_url,
            year=media_info.year,
            runtime=media_info.runtime,
            imdb_id=media_info.media_id,
            description=media_info.description,
            alt_description=media_info.alt_description,
            alt_title=media_info.as_string("alt_title"),
            language=media_info.as_string("language"),
            colour=media_info.colour,
            media_type=VisionItem.FILM,
            imdb_rating=media_info.imdb_rating,
            user_rating=media_info.user_rating,
            bonus_features=media_info.bonus_features,
            digital=media_info.digital,
            physical=media_info.physical,
            disc_index=media_info.disc_index,
            is_alt_version=media_info.is_alt_version,
        )

        if media_info.local_img_url is not None:
            item.local_img = media_info.local_img_url
        item.save(using=self._database)

        self._add_refs(item, media_info)
        self._add_alt_versions(item, media_info)
        item.save(using=self._database)

        self._created_item_count["visionitem"] += 1
        self._created_visionitems.append(str(item))

        self._db_time += time.monotonic() - t0

        return item

    def _add_refs(self, item: VisionItem, media_info: MediaInfo) -> VisionItem:
        """
        For genre, keywords, director and stars in `media_info`, add to VisionItem `item`

        Parameters
        ----------
        item : VisionItem
            VisionItem model
        media_info : MediaInfo
            MediaInfo dataclass

        Returns
        -------
        item : VisionItem
            Updated `item`
        """
        # iterate over list of genres, keywords etc
        # make new entry if necessary
        for name, model_class in self.field_map.items():
            # get db model class
            if not isinstance(name, (list, tuple)):
                # stars and director are both Person
                # turn genre and keyword into list, so can always iterate
                name = [name]
            for n in name:
                # iterate over list in MediaInfo dataclass
                for value in media_info[n]:

                    if isinstance(value, PersonInfo):
                        person_name = value.name
                        value = value.id

                    try:
                        # get ref if it exists
                        m = model_class.objects.using(self._database).get(pk=value)

                    except ObjectDoesNotExist:
                        # otherwise, make new

                        if model_class == Person:
                            # if making a new Person, ensure we have the ID and name
                            # TODO check if PersonInfo has alias field
                            args = ()
                            kwargs = {"imdb_id": value, "name": person_name}
                        else:
                            # if not Person, Model arg is just `value`
                            args = (value,)
                            kwargs = {}

                        # make new model instance
                        m = model_class(*args, **kwargs)
                        m.save(using=self._database)

                        if n in ["director", "stars"]:
                            key = "person"
                        else:
                            key = n
                        self._created_item_count[key] += 1

                    # add to VisionItem
                    # e.g. item.genre.add(m)
                    attr = getattr(item, n)
                    attr.add(m)
                    item.save(using=self._database)
        return item

    def _add_alt_versions(self, item: VisionItem, media_info: MediaInfo) -> VisionItem:
        """Add references to any alternative versions"""
        if len(media_info.alt_versions) == 0:
            return item
        else:
            for ref_film in media_info.alt_versions:
                ref_items = VisionItem.objects.using(self._database).filter(filename=ref_film)
                if len(ref_items) == 0:
                    # ref_film doesn't exist (yet) so add to _waiting_for_alt_versions
                    self._waiting_for_alt_versions.append((item, ref_film))
                    logger.info(
                        f"Alt version '{ref_film}' for {item} doesn't exist yet; added to list"
                    )
                elif len(ref_items) > 1:
                    warnings.warn(
                        f"Multiple objects with filename '{ref_film}' in database", UserWarning
                    )
                else:
                    item.alt_versions.add(ref_items[0])
                    logger.info(f"Alt version '{ref_film}' added to {item}")
            item.save(using=self._database)
        return item

    def _check_alt_versions(self):
        """Iterate through `_waiting_for_alt_versions` and add alt_versions to items"""
        if len(self._waiting_for_alt_versions) == 0:
            return

        if not self._quiet:
            progress = ProgressBar(len(self._waiting_for_alt_versions))

        for n, (item, ref_film) in enumerate(self._waiting_for_alt_versions):

            ref_items = VisionItem.objects.using(self._database).filter(filename=ref_film)
            if len(ref_items) == 0:
                warnings.warn(f"No object with filename '{ref_film}' in database", UserWarning)
            elif len(ref_items) > 1:
                warnings.warn(
                    f"Multiple objects with filename '{ref_film}' in database", UserWarning
                )
            else:
                ref_item = ref_items[0]
                if not ref_item.is_alt_version:
                    ref_item.is_alt_version = True
                    ref_item.save()
                item.alt_versions.add(ref_item)
                item.save(using=self._database)

            if not self._quiet:
                progress.progress(n + 1)

        self._waiting_for_alt_versions = []

    def _get_movie(self, title=None, patch=None, item_type="film") -> MediaInfo:
        """
        Return `MediaInfo` dataclass with data from either title or patch dict.

        Parameters
        ----------
        title : str, optional
            Film title. If not provided, you must give a `patch` dict with 'media_id'
        patch : dict, optional
            If provided, use the given 'media_id' directly and override
            IMDb values with any other values from dict.

        Returns
        -------
        info : MediaInfo
            Named tuple of info about the given film
        """

        t0 = time.monotonic()
        ret = self._media_info_processor.get_media_info(
            patch=patch, title=title, item_type=item_type
        )
        self._imdb_time += time.monotonic() - t0
        if ret is None:
            logger.warning(f"Could not get media info for {title=} {patch=}")
        return ret

    def update(self, films_txt=None, patch_csv=None) -> int:
        """
        Add any new entries to database or update existing ones.

        First, iterate over data in `patch_csv`. Then, anything listed in `films_txt` that was not
        added/updated by patch data is added.

        If `patch_csv` is provided, the corresponding item is retrieved from database.
        If any fields in the patched data don't match the DB item, it is deleted from the database
        and a new record is created using the patch.
        If there is no item in the database with the given filename, it is created.

        Either `films_txt` or `patch_csv` can be given or both. Passing no args
        raises a ValueError.

        Returns
        -------
        int
            The number of records updated
        """
        if films_txt is None and patch_csv is None:
            raise ValueError("Please specify films file and/or patch file when calling `update`")

        dct = make_combined_dict(films_txt, patch_csv)

        return self._update(dct)

    def _update(self, dct: dict[Path, dict[str, str]]) -> int:
        """
        Update/add DB entries.

        Parameters
        ----------
        dct
            Dict of patch data and films list, as returned by `make_combined_dict`.

        Returns
        -------
        int
            The number of items created or updated.
        """

        count = 0

        if len(dct) > 0:

            progress = ProgressBar(len(dct)) if not self._quiet else None

            for n, (file, info) in enumerate(dct.items()):

                item_updated = self._update_item(file, info)

                if item_updated:
                    count += 1

                if progress is not None:
                    progress.progress(n)

        self._write("Checking for remaining references...")
        self._check_alt_versions()

        self._write(f"Updated {count} records")
        return count

    def _update_item(self, file: Path, info: dict[str:Any]) -> bool:
        """
        Update or create DB item for the given `file` and `info`.
        
        Return True if an item was created/updated; otherwise False.
        """

        item = VisionItem.objects.using(self._database).filter(filename=file)

        if len(item) > 1:
            warnings.warn(f"Multiple objects with filename '{file}' in database", UserWarning)
            return False

        if len(item) == 1:
            item = item[0]
            if info is None or item_patch_equal(item, info):
                # item is already in DB with no patch data to apply
                # or all patch fields match DB item
                # skip = True
                return False
            else:
                # file in both DB and patch and the fields don't match, so re-make it
                logger.info(f"Deleting and re-creating item for '{file}'")
                item.delete()

        # if not returned yet, create or recreate item in DB
        if file.suffix == "" and "digital" not in info:
            info["digital"] = False

        if (media_info := self._get_movie(file.stem, patch=info)) is not None:
            self._add_to_db(file, media_info)
            logger.info(f"Updated {file} in DB")
            return True

        return False

    def clear(self, model=VisionItem):
        """Remove all entries from the given `model` table"""
        model.objects.using(self._database).delete()
        self._write("Cleared database")


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
    parser.add_argument(
        "-c", "--clear", help="Clear VisionItems and VisionSeries", action="store_true"
    )
    parser.add_argument("-q", "--quiet", help="Don't write anything to stdout", action="store_true")
    parser.add_argument(
        "-v", "--verbose", help="Print list of new VisionItems", action="store_true"
    )

    args = parser.parse_args()

    t0 = time.monotonic()
    pop_db = PopulateDatabase(quiet=args.quiet, physical_media=args.physical_media)

    if args.clear:
        pop_db.clear(VisionItem)
        pop_db.clear(VisionSeries)

    pop_db.update(args.films, args.patch)

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
