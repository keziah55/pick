#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
For creating and updating database entries for all films in a list of filenames.

Either import `PopulateDatabase` class or run as script. In the latter case,
see `populate_db.py -h` for options.
"""

import shutil
from pathlib import Path
import warnings
from datetime import datetime

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
from mediabrowser.models import VisionItem, Genre, Keyword, Person

from collections import namedtuple
from dataclasses import dataclass
from imdb import Cinemagoer
from imdb.Person import Person as IMDbPerson


class ProgressBar:
    """Simple ProgressBar object, going up to `maximum`"""

    def __init__(self, maximum):
        self.mx = maximum
        try:
            # get width of terminal
            width = shutil.get_terminal_size().columns
            # width of progress bar
            # 9 characters are needed for percentage etc.
            self.width = int(width) - 9
            self.show_bar = True
        except ValueError:
            # if we can't get terminal size, show only the percentage
            self.show_bar = False
        self.progress(0)

    def progress(self, value):
        """Update the progress bar

        Parameters
        ----------
        value : float
            Progress value
        """
        # calculate percentage progress
        p = value / self.mx
        show = f"{100*p:5.1f}%"

        # make bar, if required
        if self.show_bar:
            progress = int(self.width * p)
            remaining = self.width - progress
            show += " [" + "#" * progress + "-" * remaining + "]"

        # set line ending to either carriage return or new line
        end = "\r" if p < 1 else "\n"
        print(show, end=end, flush=True)


PersonInfo = namedtuple("PersonInfo", ["id", "name"])


@dataclass
class MediaInfo:
    """Class to hold info from IMDb, from which `VisionItem` can be created in database"""

    title: str
    image_url: str
    local_img_url: str
    genre: list
    keywords: list
    year: int
    runtime: int
    stars: list  # list of PersonInfo
    director: list  # list of PersonInfo
    description: str
    alt_description: str
    media_id: str
    alt_title: list
    langauge: str
    colour: bool
    alt_versions: list
    imdb_rating: float
    user_rating: float
    bonus_features: bool
    digital: bool
    physical: bool

    def __getitem__(self, key):
        value = getattr(self, key)
        return value

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def as_string(self, key) -> str:
        """
        Return field `key` as a string.

        If the value is a list, it is converted to a comma-delimited string.
        """
        value = self[key]
        if isinstance(value, list):
            value = ",".join(value)
        elif isinstance(value, int):
            value = str(value)
        if "," in value:
            value = f'"{value}"'
        return value


class PopulateDatabase:
    """Class to create records in database from list of file names"""

    field_map = {
        "genre": Genre,
        "keywords": Keyword,
        ("director", "stars"): Person,
    }

    # through_map = {'director':DirectorThrough,
    #                'stars':StarsThrough,}

    ext = [".avi", ".m4v", ".mkv", ".mov", ".mp4", ".wmv", ".webm"]

    sep = "\t"

    _error_file = Path("errors.txt")

    digital_default = True

    def __init__(self, quiet=False, physical_media=None, database="default"):

        self._created_item_count = {"visionitem": 0, "genre": 0, "keywords": 0, "person": 0}
        self._created_visionitems = []
        self._imdb_time = 0
        self._db_time = 0

        self._quiet = quiet

        self._database = database

        self._cinemagoer = Cinemagoer()

        self._direct_fields = []
        self._ref_fields = []

        for field in VisionItem._meta.get_fields():
            if field.name == "id":
                continue
            if isinstance(field, (models.ManyToManyField, models.ForeignKey)):
                self._ref_fields.append(field.name)
            else:
                self._direct_fields.append(field.name)

        self._waiting_for_alt_versions = []

        self._physical_media = (
            self._read_physical_media_csv(physical_media) if physical_media is not None else []
        )

        self._clear_error_log()

    def _write(self, s):
        if not self._quiet:
            print(s)

    @staticmethod
    def _is_id_str(s: str) -> bool:
        """Return True if string `s` can be cast to int (and thus is an ID)"""
        try:
            int(s)
        except Exception:
            return False
        else:
            return True

    def _name_to_id(self, name: str) -> str:
        """
        Given `name` string, return IMDb ID string

        Note that, if `name` is an ID string, it will simply be returned.

        Raises
        ------
        RuntimeError
           If searching for the person's name returned no values.
        """
        if not self._is_id_str(name):
            people = self._cinemagoer.search_person(name)
            if len(people) == 0:
                raise RuntimeError(f"Could not find IMDb ID for person '{s}'")
            name = people[0].getID()
        return name

    def _make_personinfo(self, person) -> PersonInfo:
        """
        Create PersonInfo for given `person`.

        Note that `person` can be an imdb.Person.Person instance, an ID string
        or a name string.
        """
        if isinstance(person, IMDbPerson):
            id_str = person.getID()
            name = person["name"]
        elif self._is_id_str(person):
            person = self._cinemagoer.get_person(person)
            id_str = person.getID()
            name = person["name"]
        else:
            id_str = self._name_to_id(person)
            name = person
        return PersonInfo(id_str, name)

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
            language=media_info.as_string("langauge"),
            colour=media_info.colour,
            media_type=VisionItem.FILM,
            imdb_rating=media_info.imdb_rating,
            user_rating=media_info.user_rating,
            bonus_features=media_info.bonus_features,
            digital=media_info.digital,
            physical=media_info.physical,
        )

        if media_info.local_img_url is not None:
            item.local_img = media_info.local_img_url
        item.save(using=self._database)

        self._add_refs(item, media_info)
        self._add_alt_versions(item, media_info)
        item.save(using=self._database)

        self._created_item_count["visionitem"] += 1
        self._created_visionitems.append(str(item))

        return item

    def _add_refs(self, item, media_info) -> VisionItem:
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

    def _add_alt_versions(self, item, media_info) -> VisionItem:
        """Add references to any alternative versions"""
        if len(media_info.alt_versions) == 0:
            return item
        else:
            for ref_film in media_info.alt_versions:
                ref_items = VisionItem.objects.using(self._database).filter(filename=ref_film)
                if len(ref_items) == 0:
                    # ref_film doesn't exist (yet) so add to _waiting_for_alt_versions
                    self._waiting_for_alt_versions.append((item, ref_film))
                elif len(ref_items) > 1:
                    warnings.warn(
                        f"Multiple objects with filename '{ref_film}' in database", UserWarning
                    )
                else:
                    item.alt_versions.add(ref_items[0])
            item.save(using=self._database)
        return item

    def _check_alt_verions(self):
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
                item.alt_versions.add(ref_items[0])
                item.save(using=self._database)

            if not self._quiet:
                progress.progress(n + 1)

        self._waiting_for_alt_versions = []

    @classmethod
    def _read_films_file(cls, films_txt) -> list:
        with open(films_txt) as fileobj:
            files = [
                Path(file.strip()) for file in list(fileobj) if Path(file.strip()).suffix in cls.ext
            ]
        return files

    @classmethod
    def _read_patch_csv(cls, patch_csv) -> dict:
        """Return dict from csv file"""
        # make patch dict
        with open(patch_csv) as fileobj:
            header, *lines = fileobj.readlines()
        _, *header = header.strip().split(cls.sep)  # drop 'filename'

        patch = {}
        for line in lines:
            line = line.strip().split(cls.sep)
            key, *values = line
            # key is filename; make dict of any other info
            dct = {header[i]: value for i, value in enumerate(values) if value}
            # in case a file is entered twice in the csv, merge the two dics
            current = patch.get(key, None)
            if current is None:
                patch[key] = dct
            else:
                current.update(dct)

        return patch

    @classmethod
    def _read_physical_media_csv(cls, media_csv) -> list:
        """Return list of films that are available on physical media"""
        with open(media_csv) as fileobj:
            header, *lines = fileobj.readlines()

        header = header.lower().strip().split(cls.sep)
        title_idx = header.index("title")
        media_type_idx = header.index("media type")

        physical = []
        for line in lines:
            line = line.lower()
            row = line.strip().split(cls.sep)
            if len(row) < len(header):
                break
            if row[media_type_idx].strip() == "film":
                physical.append(row[title_idx])

        return physical

    @staticmethod
    def _get_patched(movie, patch, imdb_key, patch_key=None, default=None):
        """Get `patch_key` from `patch`, falling back to `imdb_key` from `movie`"""
        if patch_key is None:
            patch_key = imdb_key
        value = patch.get(patch_key, movie.get(imdb_key, default))
        if value is None:
            # found instance where key was in movie, but it returned None
            value = default
        return value

    def _get_media_info(self, movie, patch=None) -> MediaInfo:
        """
        Return dataclass of info about the film from the given `movie`

        Parameters
        ----------
        movie : cinemagoer.Movie
            Movie object
        patch : dict, optional
            Dict of values to use instead of those from `movie`

        Returns
        -------
        info : MediaInfo
            Dataclass of info about the given film
        """
        if patch is None:
            patch = {}

        title = self._get_patched(movie, patch, "title", default="")

        alt_title_fields = ["original title", "localized title"]
        alt_title = set(
            [
                self._get_patched(movie, patch, field, "alt_title", default=title)
                for field in alt_title_fields
            ]
        )
        if title in alt_title:
            alt_title.remove(title)
        alt_title = list(alt_title)

        language = self._get_patched(movie, patch, "languages", "language", default=[])

        colour = self._get_patched(movie, patch, "color info", "colour", default=["Color"])
        colour = any(["color" in item.lower() for item in colour])  # boolean

        image_url = self._get_patched(movie, patch, "cover url", "image_url", default="")
        if "_V1_" in image_url:
            head, tail = image_url.split("_V1_")
            if tail:
                image_url = head + "_V1_FMjpg_UX1000_.jpg"

        local_img_url = patch.get("local_img", None)

        genre = self._get_patched(movie, patch, "genres", "genre", default=[])
        if isinstance(genre, str):
            genre = [s.strip() for s in genre.split(",") if s]

        # list of keywords
        keywords = self._get_patched(movie, patch, "keywords", default=[])
        if isinstance(keywords, str):
            keywords = [s.strip() for s in keywords.split(",") if s]

        # get release year
        year = patch.get("year", int(movie.get("year", 0)))

        # get runtime
        runtime = patch.get(
            "runtime", int(movie.get("runtimes", [0])[0])
        )  # runtimes from imdb is list of strings, want single int

        # get list of actors and director(s)
        if "stars" in patch:
            stars = ",".split(patch["stars"])
        else:
            stars = movie.get("cast", [])
        stars = [self._make_personinfo(person) for person in stars]

        if "director" in patch:
            director = ",".split(patch["director"])
        else:
            director = movie.get("director", [])
        director = [self._make_personinfo(person) for person in director]

        desc = patch.get("description", movie.get("plot", movie.get("plot outline", "")))

        alt_desc = patch.get("alt_description", "")

        media_id = patch.get("media_id", movie.getID())

        alt_versions = patch.get("alt_versions", "")
        alt_versions = [fname for fname in alt_versions.split(",") if fname]

        imdb_rating = self._get_patched(movie, patch, "rating", "imdb_rating", default=0)
        user_rating = patch.get("user_rating", 0)

        bonus_features = patch.get("bonus_features", False)
        digital = patch.get("digital", self.digital_default)
        physical = patch.get("physical", title.lower() in self._physical_media)

        info = MediaInfo(
            title,
            image_url,
            local_img_url,
            genre,
            keywords,
            year,
            runtime,
            stars,
            director,
            desc,
            alt_desc,
            media_id,
            alt_title,
            language,
            colour,
            alt_versions,
            imdb_rating,
            user_rating,
            bonus_features,
            digital,
            physical,
        )

        return info

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
            Dataclass of info about the given film
        """
        if title is None and patch is None:
            raise ValueError("PopulateDatabase._get_movie needs either title or patch")

        infoset = ["main", "keywords"]

        if patch is not None:
            try:
                movie = self._cinemagoer.get_movie(patch["media_id"])
            except Exception as err:
                self._log_error(f"{patch['media_id']}; get_movie from media_id: {err}")
                return None
            else:
                title = movie.get("title")
        else:
            try:
                movies = self._cinemagoer.search_movie(title)
            except Exception as err:
                self._log_error(f"{title}; search_movie from title: {err}")
                return None

            if len(movies) == 0:
                self._log_error(f"{title}; search_movie")
                return None

            movie = movies[0]

        if movie is None:
            self._log_error(f"{title}; no imdb results")
            return None

        try:
            self._cinemagoer.update(movie, infoset)
        except Exception as err:
            self._log_error(f"{title}; update: {err}")
            return None

        try:
            info = self._get_media_info(movie, patch)
        except Exception as err:
            info = None
            self._log_error(f"{title}; _get_media_info: {err}")
        return info

    def populate(self, films_txt, patch_csv=None) -> int:
        """
        Read file of film file names and create database entries for all

        Parameters
        ----------
        films_txt : str
            Path to file containing list of file names
        patch_csv : str
            Path to csv file of values to use instead of those returned by Cinemagoer

        Returns
        -------
        count : int
            The number of records created
        """
        if films_txt is None:
            raise ValueError(
                "You must provide a path to file containing list of films in order to populate DB"
            )
        files = self._read_films_file(films_txt)
        patch = self._read_patch_csv(patch_csv) if patch_csv is not None else {}
        return self._populate(files, patch)

    def _populate(self, files, patch={}):
        """Do populate. See `populate` for args."""
        if not self._quiet and len(files) > 0:
            progress = ProgressBar(len(files))

        for n, file in enumerate(files):

            info = patch.get(str(file), None)

            t0 = time()
            media_info = self._get_movie(file.stem, patch=info)
            t1 = time()
            self._imdb_time += t1 - t0
            if media_info is None:
                continue
            else:
                t0 = time()
                self._add_to_db(file, media_info)
                t1 = time()
                self._db_time += t1 - t0

            if not self._quiet:
                progress.progress(n + 1)

        self._write("Checking for remaining references...")
        self._check_alt_verions()

    def update(self, films_txt=None, patch_csv=None) -> int:
        """
        If `films_txt` is not None, add any new entries to the database, using
        `patch_csv`, if provided.

        If `patch_csv` is provided, the corresponding item is retrieved from database.
        If the IDs don't match, the item will be deleted from the database and a
        new record will be created using the patch.
        If there is no item in the database with the given filename, it is created.

        Either `films_txt` or `patch_csv` can be given or both. Passing no args
        raises a ValueError.

        Returns
        -------
        count : int
            The number of records updated
        """
        if films_txt is None and patch_csv is None:
            raise ValueError("Please specify films file and/or patch file when calling `update`")

        patch = self._read_patch_csv(patch_csv) if patch_csv is not None else {}
        files = (
            self._read_films_file(films_txt)
            if films_txt is not None
            else [Path(file) for file in patch.keys()]
        )
        return self._update(files, patch)

    def _update(self, files, patch={}):
        """Do update. See `update` for args."""
        if not self._quiet and len(files) > 0:
            progress = ProgressBar(len(files))

        count = 0

        for n, file in enumerate(files):

            info = patch.get(str(file), None)

            item = VisionItem.objects.using(self._database).filter(filename=file)
            if len(item) > 1:
                warnings.warn(f"Multiple objects with filename '{file}' in database", UserWarning)
            else:
                skip = False
                if len(item) == 1:
                    item = item[0]
                    if info is None or int(item.imdb_id) == int(info["media_id"]):
                        # file in DB and we don't have patch info for it, so skip it
                        # or
                        # file in both DB and patch and the IDs match
                        skip = True
                    else:
                        # file in both DB and patch and the IDs don't match, so re-make it
                        item.delete()
                # (re)create
                if not skip:
                    media_info = self._get_movie(file.stem, patch=info)
                    if file.suffix == "":
                        # if filename is name from dvds list (i.e. not actual filename with ext)
                        # set digital to False
                        media_info["digital"] = False
                    self._add_to_db(file, media_info)
                    count += 1

            if not self._quiet:
                progress.progress(n + 1)

        self._write(f"Updated {count} records")
        return count

    def clear(self, model=VisionItem):
        """Remove all entries from the given `model` table"""
        model.objects.using(self._database).delete()
        self._write("Cleared database")

    @classmethod
    def _log_error(cls, msg):
        with open(cls._error_file, "a") as fileobj:
            fileobj.write(f"[{datetime.now().isoformat()}] {msg}\n")

    def _clear_error_log(cls):
        if cls._error_file.exists():
            cls._error_file.unlink()


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
    from time import time
    from pprint import pprint

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-f", "--films", help="Path to films text file")
    parser.add_argument("-p", "--patch", help="Path to patch csv")
    parser.add_argument("-m", "--physical-media", help="Path to physical media csv")
    parser.add_argument(
        "-u",
        "--update",
        help="Call update with path to films file and/or patch csv",
        action="store_true",
    )
    parser.add_argument("-c", "--clear", help="Clear VisionItems", action="store_true")
    parser.add_argument("-q", "--quiet", help="Don't write anything to stdout", action="store_true")
    parser.add_argument(
        "-v", "--verbose", help="Print list of new VisionItems", action="store_true"
    )

    args = parser.parse_args()

    t0 = time()
    pop_db = PopulateDatabase(quiet=args.quiet, physical_media=args.physical_media)

    if args.clear:
        pop_db.clear()

    if args.update:
        pop_db.update(args.films, args.patch)
    else:
        pop_db.populate(args.films, args.patch)

    if not args.quiet:
        indent = " "

        t = time() - t0
        s = format_time(t)
        print(f"Completed in {s}")

        print("\nBreakdown:")
        print(f"Getting data from IMDb took {format_time(pop_db._imdb_time)}")
        print(f"Writing data to DB took     {format_time(pop_db._db_time)}")

        print("Created models in DB:")
        s = "".join([f"{indent}{k}: {v}" for k, v in pop_db._created_item_count.items()])
        print(s)

        if args.verbose:
            print("\nCreated VisionItems:")
            s = "".join([f"{indent}{name}" for name in pop_db._created_visionitems])
            print(s)
