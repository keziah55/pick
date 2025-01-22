from django.shortcuts import render
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem, VisionSeries, Keyword, Person
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE
from .utils import (
    get_filter_kwargs,
    GenreFilters,
    make_set,
    set_search_filters,
    get_context_from_request,
)
import re
from typing import NamedTuple
from collections import defaultdict
import warnings


class Result(NamedTuple):
    """
    Object holding a VisionItem and a match score for given search term and filters.

    Attributes
    ----------
    match
        How well this film matched the search filters
    film
        VisionItem instance
    """

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
    search_lst = _get_words(search_str)
    search_regex = "|".join(search_lst)

    # make list of VisionItems
    results = _search_vision_items(
        results, search_lst, search_regex, genre_filters, **filter_kwargs
    )

    if search_str:
        # only search people and keywords if given a search string
        results = _search_people(results, search_lst, search_regex, genre_filters, **filter_kwargs)

        if search_keywords:
            results = _search_keywords(
                results, search_lst, search_regex, genre_filters, **filter_kwargs
            )

    # dict of parent: members for Results to remove
    remove_results: dict[VisionSeries : list[Result]] = defaultdict(list)

    for result in results:
        if (parent := result.film.parent_series) is not None:
            # TODO check if parent has parents and recurse upwards
            remove_results[parent].append(result)

    for series_item, members in remove_results.items():
        best_match = max(member.match for member in members)
        results.append(Result(best_match, series_item))

    all_remove_items = {item for members in remove_results.values() for item in members}

    results = [result for result in results if result not in all_remove_items]

    results = sorted(
        results,
        key=lambda item: (item.match, item.user_rating, item.imdb_rating),
        reverse=True,
    )
    results = [result.film for result in results]

    # args to be substituted into the templates
    context = {"film_list": results, "search_str": search_str}

    return context


def _search_vision_items(
    results: list[VisionItem],
    search_lst: list[str],
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[VisionItem]:
    """
    Update `results` list with VisionItems.
    """
    # always search VisionItem by title
    for film in VisionItem.objects.filter(
        Q(title__iregex=search_regex) | Q(alt_title__iregex=search_regex), **filter_kwargs
    ):
        if not _check_include_film(film, results, genre_filters):
            continue
        # check how closely matched titles were
        if len(search_lst) == 0:
            m = 1
        else:
            intersect = [_get_intersect_size(search_lst, _get_words(film.title))]
            if film.alt_title:
                intersect.append(_get_intersect_size(search_lst, _get_words(film.alt_title)))
            m = max(intersect) / len(search_lst)
        if m > 0:
            results.append(Result(m, film))

    return results


def _search_people(
    results: list[VisionItem],
    search_lst: list[str],
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[VisionItem]:
    """
    Update `results` list with by searching Person objects.
    """
    persons = Person.objects.filter(name__iregex=search_regex) | Person.objects.filter(
        alias__iregex=search_regex
    )
    for person in persons:

        if len(search_lst) == 0:
            m = 1
        else:
            intersect = [_get_intersect_size(search_lst, _get_words(person.name))]
            if person.alias:
                intersect.append(_get_intersect_size(search_lst, _get_words(person.alias)))
            m = max(intersect) / len(search_lst)

        if m > 0:
            # get person's films, applying filters
            for field in ["stars", "director"]:
                results += [
                    Result(m, film)
                    for film in getattr(person, field).filter(**filter_kwargs)
                    if _check_include_film(film, results, genre_filters)
                ]
    return results


def _search_keywords(
    results: list[VisionItem],
    search_lst: list[str],
    search_regex: str,
    genre_filters: GenreFilters,
    **filter_kwargs,
) -> list[VisionItem]:
    """
    Update `results` list with by searching Keyword objects.
    """
    keywords = Keyword.objects.filter(name__iregex=search_regex)
    for keyword in keywords:
        if len(search_lst) == 0:
            m = 1
        else:
            m = _get_intersect_size(search_lst, _get_words(keyword.name))
        if m > 0:
            results += [
                Result(m, film)
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


def _get_words(s):
    """Return list of words in string, as lower case, with non-alphnumeric characters removed"""
    s = re.sub(r"'", "", s)  # remove apostrophes
    words = [
        word.lower() for word in re.split(r"\W", s) if word
    ]  # split on all other non-alpha characters
    return words


def _get_intersect_size(item, other):
    """
    Return the size of the intersection between the two given sets.

    Args are cast to sets if given as list or tuple.
    """
    item = make_set(item)
    other = make_set(other)
    if item is None or other is None:
        raise TypeError("_get_intersect_size args should be set, list or tuple")
    return len(item & other)
