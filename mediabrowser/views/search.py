from django.shortcuts import render
from django.db.models import Q
from ..models import VisionItem, Genre, Keyword, Person
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE
import re
from typing import NamedTuple, Optional


class Result(NamedTuple):
    """Object holding a VisionItem and a match score for given search term and filters."""

    match: float
    film: VisionItem


class GenreFilters(NamedTuple):
    """Object storing genre names for AND/OR/NOT filters."""

    genre_and: Optional[set] = None
    genre_or: Optional[set] = None
    genre_not: Optional[set] = None


def search(request, search_str):
    """Search for `search_str` across titles, people and keywords."""

    template = INDEX_TEMPLATE

    context = _get_context_from_request(request)

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

    # filter values
    filter_kwargs = {}
    if (year_min := _get_kwarg(kwargs, "year_min")) is not None and (
        year_max := _get_kwarg(kwargs, "year_max")
    ) is not None:
        filter_kwargs["year__range"] = (year_min, year_max)
    if (runtime_min := _get_kwarg(kwargs, "runtime_min")) is not None and (
        runtime_max := _get_kwarg(kwargs, "runtime_max")
    ) is not None:
        filter_kwargs["runtime__range"] = (runtime_min, runtime_max)

    if (colour := _get_kwarg(kwargs, "colour")) is not None:
        filter_kwargs["colour"] = colour
    if (black_and_white := _get_kwarg(kwargs, "black_and_white")) is not None:
        if filter_kwargs.get("colour", False) and black_and_white:
            # if both colour and black and white selected, don't filter this
            filter_kwargs.pop("colour")
        elif black_and_white:
            filter_kwargs["colour"] = False

    if (digital := _get_kwarg(kwargs, "digital")) is not None:
        filter_kwargs["digital"] = digital
    if (physical := _get_kwarg(kwargs, "physical")) is not None:
        if filter_kwargs.get("digital", False) and physical:
            # if both digital and physical selected, don't filter this
            filter_kwargs.pop("digital")
        elif physical:
            filter_kwargs["digital"] = False

    search_keywords = kwargs.get("keyword", False)

    genre_and = _make_set(kwargs.get("genre-and", None))
    genre_or = _make_set(kwargs.get("genre-or", None))
    genre_not = _make_set(kwargs.get("genre-not", None))

    genre_filters = GenreFilters(genre_and, genre_or, genre_not)

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

    results = sorted(
        results,
        key=lambda item: (item.match, item.film.user_rating, item.film.imdb_rating),
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


def set_search_filters(context, request=None) -> dict:

    # add min and max values for the sliders (not the selected min and max vals)
    if "year_range_min" not in context:
        context.update(_get_range("year"))
    if "runtime_range_min" not in context:
        context.update(_get_range("runtime"))

    if "year_min" not in context:
        context["year_min"] = context["year_range_min"]
        context["year_max"] = context["year_range_max"]

    if "runtime_min" not in context:
        context["runtime_min"] = context["runtime_range_min"]
        context["runtime_max"] = context["runtime_range_max"]

    # colour/black and white and digital/physical: if unchecked, leave it. Otherwise, set checked
    tmp_dct = {}
    names = ["keyword", "colour", "black_and_white", "digital", "physical"]
    for name in names:
        if context.get(name, False) is not False:
            tmp_dct[f"{name}_checked"] = True  # assigning to context directly here didn't work
    context.update(tmp_dct)

    # have to manually get the background colour from style.css and pass it into the template
    # 0:neutral, 1:AND, 2:OR, 3:NOT
    genres = {}
    genre_text = ["\u2015", "AND", "OR", "NOT"]
    genre_lists = [context.get(f"genre-{key}", []) for key in ["and", "or", "not"]]
    for g in Genre.objects.all():
        value = 0  # neutral by default
        for i, genre_list in enumerate(genre_lists):
            if g.name.lower() in genre_list:
                value = i + 1  # value should be 1, 2 or 3
        genres[g.name] = (str(value), genre_text[value])
    context["genres"] = genres

    if "all-genre-box-data" not in context and request is not None:
        values = set([value[0] for value in genres.values()])
        if len(values) == 1:
            value = values.pop()
        else:
            value = "0"
        context["all_genre_data"] = (
            request.GET.get("all-genre-box-data", value),
            genre_text[int(value)],
        )

    return context


def _make_set(item):
    """
    Try to cast `item` as set.

    If `item` is None, return None. Otherwise, return `item` as set.
    If `item` is not a set, list or tuple, raise TypeError.
    """
    if item is None:
        return None
    elif isinstance(item, set):
        return item
    elif isinstance(item, (list, tuple)):
        return set(item)
    else:
        raise TypeError(f"Cannot cast type {type(item)} to set")


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
    item = _make_set(item)
    other = _make_set(other)
    if item is None or other is None:
        raise TypeError("_get_intersect_size args should be set, list or tuple")
    return len(item & other)


def _get_context_from_request(request) -> dict:
    """Try to get year and runtime min and max from `request`"""
    context = {}

    # assigning to context dict in for loop with variable key names wasn't working
    # so store in separate lists
    genre_and = []
    genre_or = []
    genre_not = []

    for key, value in request.GET.items():

        if key in _get_search_kwargs():
            context[key] = value
        elif key.startswith("genre-"):
            genre = key.removeprefix("genre-").removesuffix("-data")
            match int(value):
                case 1:
                    genre_and.append(genre)
                case 2:
                    genre_or.append(genre)
                case 3:
                    genre_not.append(genre)

            # value = int(value)
            # if value == 1:
            #     genre_and.append(genre)
            # if value == 2:
            #     genre_or.append(genre)
            # elif value == 3:
            #     genre_not.append(genre)
            # else:
            #     # do nothing for neutral filter
            #     continue

    if len(genre_and) > 0:
        context["genre-and"] = genre_and
    if len(genre_or) > 0:
        context["genre-or"] = genre_or
    if len(genre_not) > 0:
        context["genre-not"] = genre_not

    return context


def _get_search_kwarg_type_map():
    type_map = {
        "year_min": int,
        "year_max": int,
        "runtime_min": int,
        "runtime_max": int,
        "keyword": bool,
        "black_and_white": bool,
        "colour": bool,
        "digital": bool,
        "physical": bool,
    }
    return type_map


def _get_search_kwargs():
    """Return list of kwarg names for search filters"""
    return list(_get_search_kwarg_type_map().keys())


def _get_kwarg(kwargs, key):
    """Get `key` from `kwargs` and cast value according to `_get_search_kwarg_type_map`"""
    type_map = _get_search_kwarg_type_map()
    value = kwargs.get(key, None)
    if value is not None:
        t = type_map.get(key, None)
        if t is not None:
            value = t(value)
    return value


def _get_range(name, model_class=VisionItem) -> dict:
    """Return dict with min and max values of `name` in the given `model_class`"""
    values = set(model_class.objects.all().values_list(name, flat=True))
    dct = {f"{name}_range_min": min(values), f"{name}_range_max": max(values)}
    return dct
