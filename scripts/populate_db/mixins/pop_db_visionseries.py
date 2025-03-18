from pathlib import Path
from typing import Union, Optional
import itertools
from functools import partial

from ..read_data_files import read_series_csv

# from ..progress_bar import ProgressBar
from ..get_db_items import get_derived_instance, get_item, filter_visionitem_visionseries
from ..logger import get_logger

from django.core.exceptions import ObjectDoesNotExist
from mediabrowser.models import VisionItem, VisionSeries, MediaItem


logger = get_logger()


class PopulateDBVisionSeriesMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # wrap db util funcs to automatically use self._database
        for func in [get_derived_instance, get_item, filter_visionitem_visionseries]:
            name = f"_{func.__name__}"
            f = partial(func, database=self._database)
            setattr(self, name, f)

    def write_series_to_db(self, csv_file: Path, sort_by_year=True) -> int:

        data = read_series_csv(csv_file)

        # progress = ProgressBar(len(data)) if not self._quiet else None
        self._writer.make_progress_bar(len(data))
        count = 0

        for n, (name, dct) in enumerate(data.items()):

            pks = dct.get("items", None)
            titles = dct.get("titles", None)
            search_str = dct.get("item_title_contains", "")
            description = dct.get("description", None)

            members = self._get_members(name, pks, titles, search_str, sort_by_year)
            if members is None:
                logger.warning(
                    f"Cannot find members for series '{name}', with {pks=}, {titles=}, {search_str=}"
                )
                continue

            try:
                series = VisionSeries.objects.get(title__iexact=name)
            except ObjectDoesNotExist:
                pass
            else:
                if [m.pk for m in series.members.all()] == [m.pk for m in members]:
                    continue

            self._make_series(members, name, description)
            count += 1

            self._writer.update_progress(n + 1)

        return count

    def _get_members(
        self, name, pks, titles, search_str, sort_by_year
    ) -> Optional[list[Union[VisionItem, VisionSeries]]]:

        if pks is not None:
            members = [self._get_item(pk) for pk in pks]
        elif titles is not None:
            members = [
                self._filter_visionitem_visionseries(title__iexact=title) for title in titles
            ]
            if any(len(sublist) != 1 for sublist in members):
                logger.warning(f"Could not identify series members from {members}")
                return None
            else:
                members = list(itertools.chain(*members))

        else:
            if not search_str:
                search_str = name
            members = self._filter_visionitem_visionseries(title__icontains=search_str)

            # sort in chronological order
            if sort_by_year:
                members.sort(key=lambda item: item.year)

        if len(members) == 0:
            return None
        else:
            return members

    def _make_series(
        self,
        items: list[Union[VisionItem, VisionSeries]],
        title: str,
        description: Optional[str] = None,
    ) -> VisionSeries:

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

            item = self._get_derived_instance(item)
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

        series.save(using=self._database)

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
            item.save(using=self._database)

        series.save(using=self._database)

        return series
