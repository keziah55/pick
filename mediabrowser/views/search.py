from django.shortcuts import render
from django.db.models import Q
from ..models import VisionItem, VisionSeries, Keyword, Person, MediaItem
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE
from .utils import (
    get_filter_kwargs,
    GenreFilters,
    set_search_filters,
    get_context_from_request,
    get_match,
    make_search_regex,
    cast_vision_items,
    filter_items_from_series,
)
from typing import NamedTuple


class Result(NamedTuple):
    """
    Object holding a VisionItem and a match score for given search term and filters.

    Attributes
    ----------
    full_target_match
        True if the target string is in the film's fields in its entirety
    match
        Proportion of target words contained in film's fields
    film
        VisionItem instance
    """

    full_target_match: bool
    match: float
    film: VisionItem

    @property
    def pk(self):
        return self.film.pk

    @property
    def user_rating(self):
        return self.film.user_rating

    @property
    def imdb_rating(self):
        return self.film.imdb_rating

    def __hash__(self):
        return self.pk


def search(request, search_str):
    """Search for `search_str` across titles, people and keywords."""

    template = INDEX_TEMPLATE

    context = get_context_from_request(request)

    search_results = _search(search_str, **context)
    context.update(search_results)
    context = set_search_filters(context, request)

    context["filmlist_template"] = FILMLIST_TEMPLATE
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        template = FILMLIST_TEMPLATE

    return render(request, template, context)


def _search(search_str, **kwargs) -> dict:
    """
    Search VisionItems for `search_str`

    If `search_str` is empty string, return all VisionItems.
    Otherwise, also search Person and Keyword tables.
    """

    filter_kwargs, search_keywords, genre_filters = get_filter_kwargs(**kwargs)

    results = []

    # search words independently
    search_regex = make_search_regex(search_str)

    # make list of VisionSeries and VisionItems
    results = _search_vision_series(
        results, search_str, search_regex, genre_filters, **filter_kwargs
    )

    results = _search_vision_items(
        results, search_str, search_regex, genre_filters, **filter_kwargs
    )

    if search_str:
        # only search people and keywords if given a search string
        results = _search_people(results, search_str, search_regex, genre_filters, **filter_kwargs)

        if search_keywords:
            results = _search_keywords(
                results, search_str, search_regex, genre_filters, **filter_kwargs
            )

    results = [
        result
        for result in results
        if result.film.parent_series is None or result.film.media_type == MediaItem.SERIES
    ]

    results = sorted(
        results,
        key=lambda item: (item.full_target_match, item.match, item.user_rating, item.imdb_rating),
        reverse=True,
    )
    results = [result.film for result in results]

    results = cast_vision_items(results)
    results = filter_items_from_series(results)

    # this is kinda nasty. would be better to figure out why there are duplicated series in results
    deduplicated_results = list(dict.fromkeys(results))

    # args to be substituted into the templates
    context = {"film_list": deduplicated_results, "search_str": search_str}

    return context


def _search_vision_series(
    results: list[Result],
    search_str: str,
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[Result]:
    """
    Update `results` list by searching titles of series.
    """
    # always search VisionItem by title
    for film in VisionSeries.objects.filter(title__iregex=search_regex, **filter_kwargs):
        if not _check_include_film(film, results, genre_filters):
            continue
        # check how closely matched titles were
        if len(search_str) == 0:
            m = 1
            target_match = False
        else:
            target_match, m = get_match(search_str, film.title)
        if m > 0:
            results.append(Result(target_match, m, film))

    return results


def _search_vision_items(
    results: list[Result],
    search_str: str,
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[Result]:
    """
    Update `results` list by searching titles of films.
    """
    # always search VisionItem by title
    for film in VisionItem.objects.filter(
        Q(title__iregex=search_regex) | Q(alt_title__iregex=search_regex), **filter_kwargs
    ):
        if not _check_include_film(film, results, genre_filters):
            continue
        # check how closely matched titles were
        if len(search_str) == 0:
            m = 1
            target_match = False
        else:
            possible = [film.title]
            if film.alt_title:
                possible.append(film.alt_title)
            target_match, m = get_match(search_str, possible)
        if m > 0:
            results.append(Result(target_match, m, film))

    return results


def _search_people(
    results: list[Result],
    search_str: str,
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[Result]:
    """
    Update `results` list by searching Person objects.
    """
    persons = Person.objects.filter(name__iregex=search_regex) | Person.objects.filter(
        alias__iregex=search_regex
    )
    for person in persons:

        if len(search_str) == 0:
            m = 1
            target_match = False
        else:
            possible = [person.name]
            if person.alias:
                possible.append(person.alias)
            target_match, m = get_match(search_str, possible)

        if m > 0:
            # get person's films, applying filters
            for field in ["stars", "director"]:
                results += [
                    Result(target_match, m, film)
                    for film in getattr(person, field).filter(**filter_kwargs)
                    if _check_include_film(film, results, genre_filters)
                ]
    return results


def _search_keywords(
    results: list[Result],
    search_str: str,
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[Result]:
    """
    Update `results` list by searching Keyword objects.
    """
    keywords = Keyword.objects.filter(name__iregex=search_regex)
    for keyword in keywords:
        if len(search_str) == 0:
            m = 1
            target_match = False
        else:
            target_match, m = get_match(search_str, keyword.name)

        if m > 0:
            results += [
                Result(target_match, m, film)
                for film in keyword.visionitem_set.filter(**filter_kwargs)
                if _check_include_film(film, results, genre_filters)
            ]
    return results


def _check_include_film(film, results, genre_filters) -> bool:
    """
    Return True if `film` not already in `results` and any of its genres are in `genres` set.

    Parameters
    ----------
    film : VisionItem
        Film to check
    results : list
        List of VisionItems
    genre_filters : GenreFilters
        Tuple of sets (of lower case strings). Each set is the genre names which:

          - must be present (and)
          - may be present (or)
          - to exclude (not)

    """
    film_is_new = film not in [result.film for result in results]
    film_genres = set([g.name.lower() for g in film.genre.all()])

    genre_and, genre_or, genre_not = genre_filters

    conditions = []  # list of AND and/or OR

    include = None
    dont_exclude = None

    if genre_and is not None:
        conditions.append(genre_and.issubset(film_genres))
    if genre_or is not None:
        conditions.append(not genre_or.isdisjoint(film_genres))
    if genre_not is not None:
        dont_exclude = genre_not.isdisjoint(film_genres)

    if len(conditions) >= 1:
        # if both AND and OR, 'or' them
        # otherwise whichever one is present
        include = any(conditions)

    ret = [value for value in (include, dont_exclude, film_is_new) if value is not None]
    return all(ret)
