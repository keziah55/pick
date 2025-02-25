import logging
from typing import NamedTuple, Optional
from imdb import Cinemagoer
from imdb.Movie import Movie
from .read_data_files import read_physical_media_csv
from .person_info import make_personinfo, PersonInfo
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

    def __init__(self, physical_media=None):
        self._movie_cache = {}
        self._cinemagoer = Cinemagoer()
        self._physical_media = (
            read_physical_media_csv(physical_media) if physical_media is not None else {}
        )

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

        infoset = ["main", "keywords"]

        if patch is not None:
            movie = self._get_movie_from_patch(patch)
        else:
            movie = self._get_movie_from_imdb(title)

        if movie is None:
            return None

        try:
            self._cinemagoer.update(movie, infoset)
        except Exception as err:
            logger.warning(f"{title}; update: {err}")
            return None

        if patch is not None and patch.get("alt_versions", None) is not None:
            media_id = patch.get("media_id", movie.getID())
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

    def _get_movie_from_patch(self, patch) -> Optional[Movie]:
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
            movie = self._cinemagoer.get_movie(media_id)
        except Exception as err:
            logger.warning(f"cinemagoer.get_movie({media_id=}) raised error: {err}")
            return None
        else:
            logger.info(f"Got {movie} by ID {media_id} from cinemagoer")

        return movie

    def _get_from_cache(self, media_id: str) -> Optional[Movie]:
        movie = self._movie_cache.get(media_id, None)
        if movie is None:
            logger.warning(f"No cached movie for id={media_id}")
        else:
            logger.info(f"Got {movie} from cache")
        return movie

    def _get_movie_from_imdb(self, title) -> Optional[Movie]:
        """Get `Movie` from IMDb by searching for title."""
        try:
            movies = self._cinemagoer.search_movie(title)
        except Exception as err:
            logger.warning(f"{title}; search_movie from title: {err}")
            return None

        if len(movies) == 0:
            logger.warning(f"{title}; search_movie")
            return None

        logger.info(f"Got {len(movies)} possible matches:\n{movies}")

        best_match = None
        for movie in movies:
            m = get_match(title, movie.get("title"))
            if best_match is None or m > best_match[1]:
                best_match = (movie, m)

        logger.info(f"Got best match {best_match[0]} with score {best_match[1]}")
        movie = best_match[0]

        return movie

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

    def _make_media_info(self, movie: Movie, patch=None) -> MediaInfo:
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
        if not isinstance(colour, bool):
            colour = any("color" in item.lower() for item in colour)  # boolean

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
        stars = [make_personinfo(person, self._cinemagoer) for person in stars]

        if "director" in patch:
            director = ",".split(patch["director"])
        else:
            director = movie.get("director", [])
        director = [make_personinfo(person, self._cinemagoer) for person in director]

        desc = patch.get("description", movie.get("plot", movie.get("plot outline", "")))
        if isinstance(desc, list):
            desc = desc[0]

        alt_desc = patch.get("alt_description", "")

        media_id = patch.get("media_id", movie.getID())

        alt_versions = patch.get("alt_versions", "")
        alt_versions = [fname for fname in alt_versions.split(",") if fname]

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
