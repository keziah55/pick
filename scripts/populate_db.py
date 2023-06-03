#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
For creating and updating database entries for all films in a list of filenames.

Either import `PopulateDatabase` class or run as script. In the latter case,
see `populate_db.py -h` for options.
"""

import os
import shutil
import warnings
from datetime import datetime

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pick.settings')
    import django
    django.setup()

from django.db import models
from django.core.exceptions import ObjectDoesNotExist    
from mediabrowser.models import VisionItem, MediaSeries, Genre, Keyword, Person

from dataclasses import dataclass
from imdb import Cinemagoer

class ProgressBar:
    """ Simple ProgressBar object, going up to `maximum` """
    def __init__(self, maximum):
        self.mx = maximum
        try:
            # get width of terminal
            width = shutil.get_terminal_size().columns
            # width of progress bar
            # 9 characters are needed for percentage etc.
            self.width = int(width)-9
            self.show_bar = True
        except ValueError:
            # if we can't get terminal size, show only the percentage
            self.show_bar = False
        self.progress(0)
        
    def progress(self, value):
        """ Update the progress bar
        
            Parameters
            ----------
            value : float
                Progress value
        """
        # calculate percentage progress
        p = value/self.mx
        show = f'{100*p:5.1f}%'
        
        # make bar, if required
        if self.show_bar:
            progress = int(self.width*p)
            remaining = self.width-progress
            show += ' [' + '#'*progress + '-'*remaining + ']'
        
        # set line ending to either carriage return or new line
        end = '\r' if p < 1 else '\n'
        print(show, end=end, flush=True)
        
@dataclass
class MediaInfo:
    """ Class to hold info from IMDb, from which `VisionItem` can be created in database """
    title: str
    image_url: str
    genre: list
    keywords: list
    year: int
    runtime: int
    stars: list
    director: list
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
    
    def as_string(self, key) -> str:
        """ 
        Return field `key` as a string.
        
        If the value is a list, it is converted to a comma-delimited string.
        """
        value = self[key]
        if isinstance(value, list):
            value = ','.join(value)
        elif isinstance(value, int):
            value = str(value)
        if ',' in value:
            value = f'"{value}"'
        return value

class PopulateDatabase:
    """ Class to create records in database from list of file names """
    
    field_map = {'genre': Genre,
                 'keywords': Keyword,
                 ('director','stars'): Person,}
    
    # through_map = {'director':DirectorThrough,
    #                'stars':StarsThrough,}
    
    ext = ['.avi', '.m4v', '.mkv', '.mov', '.mp4', '.wmv']
    
    sep = "\t"
    
    def __init__(self, quiet=False):
        
        self._quiet = quiet
        
        self._direct_fields = []
        self._ref_fields = []
        
        for field in VisionItem._meta.get_fields():
            if field.name == 'id':
                continue
            if isinstance(field, (models.ManyToManyField, models.ForeignKey)):
                self._ref_fields.append(field.name)
            else:
                self._direct_fields.append(field.name)
                
        self._waiting_for_alt_versions = []
        
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
        item = VisionItem(
            title = media_info.title,
            filename = filename,
            img = media_info.image_url,
            year = media_info.year,
            runtime = media_info.runtime,
            imdb_id = media_info.media_id,
            description = media_info.description,
            alt_description = media_info.alt_description,
            alt_title = media_info.as_string('alt_title'),
            language = media_info.as_string('langauge'),
            colour = media_info.colour,
            media_type = VisionItem.FILM,
            imdb_rating = media_info.imdb_rating,
            user_rating = media_info.user_rating,
            bonus_features = media_info.bonus_features,
            digital = media_info.digital,
            physical = media_info.physical,
        )
        item.save()
        
        self._add_refs(item, media_info)
        self._add_alt_versions(item, media_info)
        item.save()
        
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
            if not isinstance(name, (list,tuple)):
                # stars and director are both Person
                # turn genre and keyword into list, so can always iterate
                name = [name]
            for n in name:
                # iterate over list in MediaInfo dataclass
                for value in media_info[n]:
                    try:
                        # get ref if it exists
                        m = model_class.objects.get(pk=value)
                    except ObjectDoesNotExist:
                        # otherwise, make new
                        m = model_class(value)
                        m.save()
                        
                    # # make custom through table to preserve insertion order
                    # through_class = self.through_map.get(n, None)
                    # if through_class is not None:
                    #     through = through_class(person=m, mediaitem=item)
                    #     through.save()
                        
                    # add to VisionItem
                    # e.g. item.genre.add(m)
                    attr = getattr(item, n)
                    attr.add(m)
                    item.save()
        return item
    
    def _add_alt_versions(self, item, media_info) -> VisionItem:
        """ Add references to any alternative versions """
        if len(media_info.alt_versions) == 0:
            return item
        else:
            for ref_film in media_info.alt_versions:
                ref_items = VisionItem.objects.filter(filename=ref_film)
                if len(ref_items) == 0:
                    # ref_film doesn't exist (yet) so add to _waiting_for_alt_versions
                    self._waiting_for_alt_versions.append((item, ref_film))
                elif len(ref_items) > 1:
                    warnings.warn(f"Multiple objects with filename '{ref_film}' in database", UserWarning)
                else:
                    item.alt_versions.add(ref_items[0])
            item.save()
        return item
    
    def _check_alt_verions(self):
        """ Iterate through `_waiting_for_alt_versions` and add alt_versions to items """
        if len(self._waiting_for_alt_versions) == 0:
            return
        
        if not self._quiet:
            progress = ProgressBar(len(self._waiting_for_alt_versions))
        
        for n, (item, ref_film) in enumerate(self._waiting_for_alt_versions):
            
            ref_items = VisionItem.objects.filter(filename=ref_film)
            if len(ref_items) == 0:
                warnings.warn(f"No object with filename '{ref_film}' in database", UserWarning)
            elif len(ref_items) > 1:
                warnings.warn(f"Multiple objects with filename '{ref_film}' in database", UserWarning)
            else:
                item.alt_versions.add(ref_items[0])
                item.save()
                
            if not self._quiet:
                progress.progress(n+1)
                
        self._waiting_for_alt_versions = []
    
    @classmethod   
    def _read_patch_csv(cls, patch_csv) -> dict:
        """ Return dict from csv file """
        # make patch dict
        with open(patch_csv) as fileobj:
            header, *lines = fileobj.readlines()
        _, *header = header.strip().split(cls.sep) # drop 'filename'
        
        patch = {}
        for line in lines:
            line = line.strip().split(cls.sep)
            key, *values = line
            # key is filename; make dict of any other info
            patch[key] = {header[i]:value for i, value in enumerate(values) if value}
        
        return patch
        
    @staticmethod
    def _get_patched(movie, patch, imdb_key, patch_key=None, default=None):
        """ Get `patch_key` from `patch`, falling back to `imdb_key` from `movie` """
        if patch_key is None:
            patch_key = imdb_key
        value = patch.get(patch_key, movie.get(imdb_key, default))
        if value is None:
            # found instance where key was in movie, but it returned None
            value = default
        return value
    
    @classmethod
    def _get_media_info(cls, movie, patch=None) -> MediaInfo:
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
        
        title = cls._get_patched(movie, patch, 'title', default='') 
        
        alt_title_fields = ['original title', 'localized title']
        alt_title = set([cls._get_patched(movie, patch, field, 'alt_title', default=title) for field in alt_title_fields])
        if title in alt_title:
            alt_title.remove(title)
        alt_title = list(alt_title)
        
        language = cls._get_patched(movie, patch, 'languages', 'language', default=[])
        
        colour = cls._get_patched(movie, patch, 'color info', 'colour', default=['Color'])
        colour = any(['color' in item.lower() for item in colour]) # boolean
        
        image_url = cls._get_patched(movie, patch, 'cover url', 'image_url', default='')
        if '_V1_' in image_url:
            head, tail = image_url.split('_V1_')
            if tail:
                image_url = head + "_V1_FMjpg_UX1000_.jpg"
        
        genre = cls._get_patched(movie, patch, 'genres', 'genre', default=[])
        if isinstance(genre, str):
            genre = [s.strip() for s in genre.split(',') if s]
        
        # list of keywords
        keywords = cls._get_patched(movie, patch, 'keywords', default=[])
        if isinstance(keywords, str):
            keywords = [s.strip() for s in keywords.split(',') if s]
        
        # get release year
        year = patch.get('year', int(movie.get('year', 0)))
        
        # get runtime
        runtime = patch.get('runtime', int(movie.get('runtimes', [0])[0])) # runtimes from imdb is list of strings, want single int
        
        # get list of actors and director(s)
        if 'stars' in patch:
            stars = ','.split(patch['stars'])
        else:
            stars = [person['name'] for person in movie.get('cast', [])]
        
        if 'director' in patch:
            director = ','.split(patch['director'])
        else:
            director = [person['name'] for person in movie.get('director', [])]
        
        desc = patch.get('description', movie.get('plot', movie.get('plot outline', '')))
        
        alt_desc = patch.get('alt_description', '')
        
        media_id = patch.get('media_id', movie.getID())
        
        alt_versions = patch.get('alt_versions', '')
        alt_versions = [fname for fname in alt_versions.split(',') if fname]
        
        imdb_rating = cls._get_patched(movie, patch, 'rating', 'imdb_rating', default=0)
        user_rating = patch.get('user_rating', 0)
        
        bonus_features = patch.get('bonus_features', False)
        digital = patch.get('digital', True)
        physical = patch.get('physical', False)
        
        info = MediaInfo(
            title, image_url, genre, keywords, year, runtime, stars, director, 
            desc, alt_desc, media_id, alt_title, language, colour, alt_versions, 
            imdb_rating, user_rating, bonus_features, digital, physical
        )
        
        return info
        
    @classmethod
    def _get_movie(cls, title=None, patch=None, item_type='film') -> MediaInfo:
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
            
        cinemagoer = Cinemagoer()
        infoset = ['main', 'keywords']
        
        if patch is not None:
            movie = cinemagoer.get_movie(patch['media_id'])
            title = movie.get('title')
        else:
            movies = cinemagoer.search_movie(title)
            
            if len(movies) == 0:
                with open("errors.txt", "a") as fileobj:
                    fileobj.write(f"[{datetime.now().isoformat()}] {title}; search_movie\n")
                return None
            
            movie = movies[0]
        
        if movie is None:
            with open("errors.txt", "a") as fileobj:
                fileobj.write(f"[{datetime.now().isoformat()}] {title}; no imdb results\n")
            return None
        
        try:
            cinemagoer.update(movie, infoset)
        except Exception as err:
            with open("errors.txt", "a") as fileobj:
                fileobj.write(f"[{datetime.now().isoformat()}] {title}; update: {err}\n")
            return None
        
        try:
            info = cls._get_media_info(movie, patch)
        except Exception as err:
            info = None
            with open("errors.txt", "a") as fileobj:
                fileobj.write(f"[{datetime.now().isoformat()}]{title}; _get_media_info: {err}\n")
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
        
        # read file names
        with open(films_txt) as fileobj:
            files = [file.strip() for file in list(fileobj) if os.path.splitext(file.strip())[-1] in self.ext]
            
        patch = self._read_patch_csv(patch_csv) if patch_csv is not None else {}
            
        if not self._quiet:
            progress = ProgressBar(len(files))
            
        for n, file in enumerate(files):
            title = os.path.splitext(os.path.basename(file))[0]
            
            info = patch.get(file, None)
            
            media_info = self._get_movie(title, patch=info)
            if media_info is None:
                continue
            else:
                self._add_to_db(file, media_info)
                
            if not self._quiet:
                progress.progress(n+1)
                
        self._write("Checking for remaining references...")
        self._check_alt_verions()

    def update(self, patch_csv) -> int:
        """ 
        For all entries in patch_csv file, retrieve the corresponding item from database 
    
        If the IDs don't match, the item will be deleted from the database and a 
        new record will be created using the patch.
        
        If there is no item in the database with the given filename, it is created.
        
        Returns
        -------
        count : int
            The number of records updated
        """
        count = 0
        patch = self._read_patch_csv(patch_csv)
        
        if not self._quiet:
            progress_count = 0
            progress = ProgressBar(len(patch))
        
        for file, dct in patch.items():
            item = VisionItem.objects.filter(filename=file)
            if len(item) > 1:
                warnings.warn(f"Multiple objects with filename '{file}' in database", UserWarning)
            else:
                skip = False
                if len(item) == 1:
                    item = item[0]
                    if int(item.imdb_id) == int(dct['media_id']):
                        skip = True
                    else:
                        item.delete()
                # (re)create
                if not skip:
                    media_info = self._get_movie(patch=dct)
                    self._add_to_db(file, media_info)
                    count += 1
                    
            if not self._quiet:
                progress_count += 1
                progress.progress(progress_count)
                 
        self._write(f"Updated {count} records")
        return count
    
    def clear(self, model=VisionItem):
        """ Remove all entries from the given `model` table """
        model.objects.all().delete()
        self._write("Cleared database")
        
if __name__ == "__main__":
    
    import argparse
    from time import time

    parser = argparse.ArgumentParser(description=__doc__)
    
    parser.add_argument('-f', '--films', help='Path to films text file')
    parser.add_argument('-p', '--patch', help='Path to patch csv')
    parser.add_argument('-u', '--update', help='Call update with path to patch csv',
                        action='store_true')
    parser.add_argument('-c', '--clear', help='Clear VisionItems', action='store_true')
    parser.add_argument('-q', '--quiet', help='Dont write anything to stdout', action='store_true')
    
    args = parser.parse_args()
    
    t0 = time()
    pop_db = PopulateDatabase(quiet=args.quiet)
    
    if args.clear:
        pop_db.clear()
    
    if args.films is not None:
        pop_db.populate(args.films, args.patch)
        
    if args.update and args.patch is not None:
        pop_db.update(args.patch)
        
    if not args.quiet:
        t = (time() - t0) / 60 # time in minutes
        hours, minssecs = divmod(t, 60)
        mins, secs = divmod((minssecs*60), 60)
        if hours > 0:
            s = f"{hours:02.0f}h{mins:02.0f}m{secs:02.0f}s"
        else:
            s = f"{mins:02.0f}m{secs:02.0f}s"
        print(f"Completed in {s}")