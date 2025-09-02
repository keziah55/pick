import logging
import re
from typing import NamedTuple, Optional

import imdbinfo
from imdbinfo.models import MovieBriefInfo, MovieDetail, SearchResult

from .read_data_files import read_physical_media_csv, read_alias_csv
from .person_info import make_personinfo, PersonInfo
from .utils import imdb_id_to_str
from mediabrowser.views.utils import get_match

logger = logging.getLogger("populate_db")


class MediaInfo(NamedTuple):
    """Class to hold info from IMDb, from which `VisionItem` can be created in database"""

    title: str
    image_url: str
    local_img_url: str
    genre: list[str]
    keywords: list[str]
    year: int
    runtime: int
    stars: list[PersonInfo]
    director: list[PersonInfo]
    description: str
    alt_description: str
    media_id: str
    alt_title: list[str]
    language: str
    colour: bool
    alt_versions: list[str]
    is_alt_version: bool
    imdb_rating: float
    user_rating: float
    bonus_features: bool
    digital: bool
    physical: bool
    disc_index: str

    def __repr__(self):
        return f"MediaInfo<{self.title} ({self.year}), {self.media_id=}>"

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
            value = ",".join(value)
        elif isinstance(value, int):
            value = str(value)
        if "," in value:
            value = f'"{value}"'
        return value


class MediaInfoProcessor:

    digital_default = True

    def __init__(self, physical_media=None, alias_csv=None):
        self._movie_cache = {}
        self._physical_media = (
            read_physical_media_csv(physical_media) if physical_media is not None else {}
        )
        self._aliases = read_alias_csv(alias_csv) if alias_csv is not None else {}

        self._media_types = ["movie", "short", "tvSeries", "tvSeriesEpisode", "tvMovie"]

    def get_media_info(
        self, patch: Optional[dict] = None, title: Optional[str] = None, item_type="film"
    ) -> Optional[MediaInfo]:
        """
        Return `MediaInfo` object for the given patch or title.

        If `patch` dict is given, that data will be used to get the IMDb movie. Otherwise, search for
        `title` string.

        Parameters
        ----------
        patch
            Dict with data to use when creating `MediaInfo`. Any fields not provided are found from IMDb.
        title
            If not providing `patch` dict, provide film title to search for,
        item_type
            Currently unused.

        Returns
        -------
        MediaInfo
            Object containing data ready to be added to database.
        None
            If no movie could be found or an exception was raised. Check the log for information.
        """
        if title is None and patch is None:
            raise ValueError("PopulateDatabase._get_movie needs either title or patch")

        if patch is not None and "media_id" in patch:
            movie = self._get_movie_from_patch(patch)
        else:
            movie = self._get_movie_from_imdb(title)

        if movie is None:
            return None

        if type(movie) is MovieBriefInfo:
            movie: MovieDetail = imdbinfo.get_movie(movie.id)

        if (media_type := movie.kind) not in self._media_types:
            logger.warning(f"{title}: got movie {movie} of type {media_type}")
            return None

        if patch is not None and patch.get("alt_versions", None) is not None:
            media_id = patch.get("media_id", movie.id)
            self._movie_cache[media_id] = movie
            logger.info(f"Caching movie with key {media_id}")

        try:
            info = self._make_media_info(movie, patch)
        except Exception as err:
            info = None
            logger.warning(f"{title}; _make_media_info: {err}")
        else:
            logger.info(f"Made MediaInfo object {info}")
        return info

    def _get_movie_from_patch(self, patch) -> Optional[MovieDetail]:
        """
        Get `Movie` from `patch` data.

        If `patch["is_alt_version"]` is True, this tries to get from cache. Otherwise (or if cache
        query unsuccessful), use `patch["media_id"]` to get from IMDb.
        """
        movie = None
        logger.info(f"{patch=}")
        media_id = patch["media_id"]

        if patch.get("is_alt_version", False):
            movie = self._get_from_cache(media_id)
            if movie is not None:
                # if got from cache successfully, return early
                return movie

        try:
            movie: MovieDetail = imdbinfo.get_movie(imdb_id_to_str(media_id))
        except Exception as err:
            logger.warning(f"cinemagoer.get_movie({media_id=}) raised error: {err}")
            return None
        else:
            logger.info(f"Got {movie} by ID {media_id} from cinemagoer")

        return movie

    def _get_from_cache(self, media_id: str) -> Optional[MovieDetail]:
        movie = self._movie_cache.get(media_id, None)
        if movie is None:
            logger.warning(f"No cached movie for id={media_id}")
        else:
            logger.info(f"Got {movie} from cache with id={media_id}")
        return movie

    def _get_movie_from_imdb(self, title) -> Optional[MovieBriefInfo]:
        """Get `Movie` from IMDb by searching for title."""
        title, year = self._parse_title(title)
        movies = self._search_imdb_by_title(title)
        if movies is None:
            return None
        else:
            return self._get_best_match(title, movies, year=year)

    @staticmethod
    def _parse_title(title) -> tuple[str, Optional[int]]:
        """Return title and optionally year, from file title."""
        title = re.sub("_", " ", title)

        if (m := re.search(r"(?P<title>.+) (\(?[E|e]xtended\)?)", title)) is not None:
            title = m.group("title").strip()

        if (m := re.search(r"(?P<title>.+)\((?P<year>\d{4})\)", title)) is not None:
            year = int(m.group("year"))
            title = m.group("title").strip()
        else:
            year = None

        return title, year

    def _search_imdb_by_title(self, title) -> Optional[list[MovieBriefInfo]]:

        logger.info(f"Search IMDb for {title=}")
        try:
            results: SearchResult = imdbinfo.search_title(title)
            movies: list[MovieBriefInfo] = results.titles
        except Exception as err:
            logger.warning(f"{title}; search_movie from title: {err}")
            return None

        if len(movies) == 0:
            logger.warning(f"Found no possible matches for {title=}")
            return None
        else:
            logger.info(f"Got {len(movies)} possible matches")

        movies = [
            movie
            for movie in movies
            if movie.cover_url is not None and movie.kind in self._media_types
        ]

        if len(movies) == 0:
            logger.warning(f"After filtering, found no possible matches for {title=}")
            return None
        else:
            logger.info(f"After filtering, got {len(movies)} possible matches:\n{movies}")

        return movies

    @staticmethod
    def _get_best_match(title: str, movies: list[MovieBriefInfo], year=None) -> MovieBriefInfo:
        logger.info("Checking for best match...")

        best_match = None

        for movie in movies:
            full_target_match, m = get_match(title, movie.title)
            if m < 0.5:
                continue

            if year is not None:
                if movie.year != year:
                    continue

            if best_match is None or (m > best_match[1] and full_target_match):
                best_match = (movie, m, full_target_match)

        if best_match is None:
            logger.error(f"Could not find match for {title} from movie list")
            return None
        else:
            s = f"{best_match[0]}"
            if (y := best_match[0].year) is not None:
                s += f" ({y})"
            logger.info(f"Got best match {s} with score {best_match[1]:.3f}")
            movie = best_match[0]

            return movie

    @staticmethod
    def _get_patched(movie, patch, imdb_key, patch_key=None, default=None):
        """Get `patch_key` from `patch`, falling back to `imdb_key` from `movie`"""
        if patch_key is None:
            patch_key = imdb_key
        value = patch.get(patch_key, getattr(movie, imdb_key, default))
        if value is None:
            # found instance where key was in movie, but it returned None
            value = default
        return value

    def _make_person_info(self, person):
        return make_personinfo(person, self._aliases)

    def _make_media_info(self, movie: MovieDetail, patch=None) -> MediaInfo:
        """
        Return named tuple of info about the film from the given `movie`.

        Parameters
        ----------
        movie : cinemagoer.Movie
            Movie object
        patch : dict, optional
            Dict of values to use instead of those from `movie`

        Returns
        -------
        info : MediaInfo
            Named tuple of info about the given film
        """
        if patch is None:
            patch = {}

        title = self._get_patched(movie, patch, "title", default="")

        alt_title_patch = patch.get("alt_title", None)
        local_title_imdb = movie.title_localized
        title_akas_imdb = movie.title_akas
        alt_title = set(title_akas_imdb) | {alt_title_patch, local_title_imdb}
        alt_title = list(filter(lambda s: s is not None and s != title, list(alt_title)))

        language = self._get_patched(movie, patch, "languages", "language", default=[])

        colour = self._get_patched(movie, patch, "colorations", "colour", default=["Color"])
        if not isinstance(colour, bool):
            colour = any("color" in item.lower() for item in colour)  # boolean

        image_url = self._get_patched(movie, patch, "cover_url", "image_url", default="")
        if "_V1_" in image_url:
            head, tail = image_url.split("_V1_")
            if tail:
                image_url = head + "_V1_FMjpg_UX1000_.jpg"

        local_img_url = patch.get("local_img", None)

        genre = self._get_patched(movie, patch, "genres", "genre", default=[])
        if isinstance(genre, str):
            genre = [s.strip() for s in genre.split(",") if s]

        # list of keywords
        keywords = self._get_patched(movie, patch, "storyline_keywords", default=[])
        if isinstance(keywords, str):
            keywords = [s.strip() for s in keywords.split(",") if s]
        # keywords = []

        # get release year
        year = patch.get("year", movie.year)

        # get runtime
        runtime = patch.get("runtime", movie.duration)

        # get list of actors and director(s)
        if "stars" in patch:
            stars = ",".split(patch["stars"])
        else:
            stars = movie.categories["cast"]  # movie.stars is first 4 billed
        stars = [self._make_person_info(person) for person in stars]

        if "director" in patch:
            director = ",".split(patch["director"])
        else:
            director = movie.directors
        director = [self._make_person_info(person) for person in director]

        desc = patch.get("description", movie.plot)
        if isinstance(desc, list):
            desc = desc[0]

        alt_desc = patch.get("alt_description", "")

        media_id = patch.get("media_id", movie.id)

        alt_versions = patch.get("alt_versions", [])
        # alt_versions = [fname for fname in alt_versions.split(",") if fname]

        imdb_rating = self._get_patched(movie, patch, "rating", "imdb_rating", default=0)
        user_rating = patch.get("user_rating", 0)

        bonus_features = patch.get("bonus_features", False)
        digital = patch.get("digital", self.digital_default)

        disc_index = patch.get("disc_index", self._physical_media.get(title.lower(), ""))
        physical = patch.get("physical", disc_index != "")

        is_alt_version = patch.get("is_alt_version", False)

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
            is_alt_version,
            imdb_rating,
            user_rating,
            bonus_features,
            digital,
            physical,
            disc_index,
        )

        return info
