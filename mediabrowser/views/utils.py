from ..models import VisionItem, Genre
from typing import NamedTuple, Optional


class GenreFilters(NamedTuple):
    """Object storing genre names for AND/OR/NOT filters."""

    genre_and: Optional[set] = None
    genre_or: Optional[set] = None
    genre_not: Optional[set] = None


def get_filter_kwargs(**kwargs) -> tuple[dict, bool, GenreFilters]:
    """
    Parse kwargs to get filter settings.

    Returns
    -------
    dict
        Dict of `filter` kwargs
    bool
        True if requested to search keywords. Default is False.
    GenreFilters
        Object with genre names and logical operation for each.
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

    genre_and = make_set(kwargs.get("genre-and", None))
    genre_or = make_set(kwargs.get("genre-or", None))
    genre_not = make_set(kwargs.get("genre-not", None))

    genre_filters = GenreFilters(genre_and, genre_or, genre_not)

    return filter_kwargs, search_keywords, genre_filters


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


def get_context_from_request(request) -> dict:
    """Try to get year and runtime min and max from `request`"""
    context = {}

    # assigning to context dict in for loop with variable key names wasn't working
    # so store in separate lists
    genre_and = []
    genre_or = []
    genre_not = []

    for key, value in request.GET.items():
        if key in search_kwargs():
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

    if len(genre_and) > 0:
        context["genre-and"] = genre_and
    if len(genre_or) > 0:
        context["genre-or"] = genre_or
    if len(genre_not) > 0:
        context["genre-not"] = genre_not

    return context


def make_set(item):
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


def search_kwargs():
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