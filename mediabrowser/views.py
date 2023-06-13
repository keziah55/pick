from django.shortcuts import render
from django.views.generic.list import ListView
from django.db.models import Q
from .models import VisionItem, MediaSeries, Genre, Keyword, Person
import re
from collections import namedtuple
from pprint import pprint

Result = namedtuple('Result', ['match', 'film'])

def index(request, template='mediabrowser/index.html', filmlist_template='mediabrowser/filmlist.html'):
    # see if the `request` object has a 'search' item
    try:
        search_str = request.GET['search']
    # if not, use empty string
    except:
        search_str = ''
        
    return search(request, search_str, template=template, filmlist_template=filmlist_template)
    
def search(request, search_str, template='mediabrowser/index.html', 
            filmlist_template='mediabrowser/filmlist.html'):
    
    context = _get_context_from_request(request)
    
    search_results = _search(search_str, **context)
    context.update(search_results)
    context = _set_search_filters(context, request)
    
    context['filmlist_template'] = filmlist_template
    if request.headers.get('x-requested-with') == 'XMLHttpRequest': 
        template = filmlist_template
    return render(request, template, context)

def _search(search_str, **kwargs) -> dict:
    """ 
    Search VisionItems for `search_str` 
    
    If `search_str` is empty string, return all VisionItems. 
    Otherwise, also search Person and Keyword tables.
    """
    
    # filter values
    filter_kwargs = {}
    if (year_min:=_get_kwarg(kwargs, 'year_min')) is not None and (year_max:=_get_kwarg(kwargs, 'year_max')) is not None:
        filter_kwargs['year__range'] = (year_min, year_max)
    if (runtime_min:=_get_kwarg(kwargs, 'runtime_min')) is not None and (runtime_max:=_get_kwarg(kwargs, 'runtime_max')) is not None:
        filter_kwargs['runtime__range'] = (runtime_min, runtime_max)
        
    if (colour:=_get_kwarg(kwargs, 'colour')) is not None:
        filter_kwargs['colour'] = colour
    if (black_and_white:=_get_kwarg(kwargs, 'black_and_white')) is not None:
        if filter_kwargs.get('colour', False) and black_and_white:
            # if both colour and black and white selected, don't filter this
            filter_kwargs.pop('colour')
        elif black_and_white:
            filter_kwargs['colour'] = False
            
    if (digital:=_get_kwarg(kwargs, 'digital')) is not None:
        filter_kwargs['digital'] = digital
    if (physical:=_get_kwarg(kwargs, 'physical')) is not None:
        if filter_kwargs.get('digital', False) and physical:
            # if both digital and physical selected, don't filter this
            filter_kwargs.pop('digital')
        elif physical:
            filter_kwargs['digital'] = False
            
    search_keywords = kwargs.get('keyword', False)
            
    genre_and = kwargs.get('genre-and', None)
    genre_or = kwargs.get('genre-or', None)
    genre_not = kwargs.get('genre-not', None)
    
    results = []
    
    # search words independently
    search_lst = _get_words(search_str)
    search_regex = "|".join(search_lst)
    
    results = []
    # always search VisionItem by title
    for film in VisionItem.objects.filter(
            Q(title__iregex=search_regex) | Q(alt_title__iregex=search_regex), 
            **filter_kwargs):
        if not _check_include_film(film, results, genre_and, genre_or, genre_not):
            continue
        # check how closely matched titles were
        if len(search_lst) == 0:
            match = 1
        else:
            intersect = [_get_intersect_size(search_lst, _get_words(film.title))]
            if film.alt_title:
                intersect.append(_get_intersect_size(search_lst, _get_words(film.alt_title)))
            match = max(intersect) / len(search_lst)
        if match > 0:
            results.append(Result(match, film))
    
    if search_str:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__iregex=search_regex) | Person.objects.filter(alias__iregex=search_regex)
        for person in persons:
            
            if len(search_lst) == 0:
                match = 1
            else:
                intersect = [_get_intersect_size(search_lst, _get_words(person.name))]
                if person.alias:
                    intersect.append(_get_intersect_size(search_lst, _get_words(person.alias)))
                match = max(intersect) / len(search_lst)
            
            if match > 0:
                # get person's films, applying filters
                results += [Result(match, film) for film in person.stars.filter(**filter_kwargs) 
                            if _check_include_film(film, results, genre_and, genre_or, genre_not)]
                results += [Result(match, film) for film in person.director.filter(**filter_kwargs) 
                            if _check_include_film(film, results, genre_and, genre_or, genre_not)]
        if search_keywords:
            keywords = Keyword.objects.filter(name__iregex=search_regex)
            for keyword in keywords:
                if len(search_lst) == 0:
                    match = 1
                else:
                    match = _get_intersect_size(search_lst, _get_words(keyword.name))
                if match > 0:
                    results += [Result(match, film) for film in keyword.visionitem_set.filter(**filter_kwargs) 
                                if _check_include_film(film, results, genre_and, genre_or, genre_not)]
    
    results = sorted(results, key=_sort_search, reverse=True)
    results = [result.film for result in results]
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_str':search_str}
    
    return context

def _check_include_film(film, results, genre_and=None, genre_or=None, genre_not=None) -> bool:
    """ 
    Return True if `film` not already in `results` and any of its genres are in `genres` set.
    
    Parameters
    ----------
    film : VisionItem
        Film to check
    results : list
        List of VisionItems
    genre_and : {set, list, tuple}, optional
        Set of genre names that must all be present in film's genres (as lower case strings)
    genre_or : {set, list, tuple}, optional
        Set of genre names any of which can be present in film's genres (as lower case strings)
    genre_not : {set, list, tuple}, optional
        Set of genre names to exclude (as lower case strings)
    """
    film_is_new = film not in [result.film for result in results]
    film_genres = set([g.name.lower() for g in film.genre.all()])
    
    # this is all very complicated, but it seems to work
    genre_and = _make_set(genre_and)
    genre_or = _make_set(genre_or)
    genre_not = _make_set(genre_not)
    
    conditions = [] # list of AND and/or OR
    
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
        
def _get_context_from_request(request) -> dict:
    """ Try to get year and runtime min and max from `request` """
    context = {}
    
    # assigning to context dict in for loop with variable key names wasn't working
    # so store in separate lists
    genre_and = []
    genre_or = []
    genre_not = []
    
    for key, value in request.GET.items():
        
        if key in _get_search_kwargs():
            context[key] = value
        elif key.startswith('genre-'):
            genre = key.removeprefix('genre-').removesuffix('-data')
            value = int(value)
            if value == 1:
                genre_and.append(genre)
            if value == 2:
                genre_or.append(genre)
            elif value == 3:
                genre_not.append(genre)
            else:
                # do nothing for neutral filter
                continue
            
    if len(genre_and) > 0:
        context['genre-and'] = genre_and
    if len(genre_or) > 0:
        context['genre-or'] = genre_or
    if len(genre_not) > 0:
        context['genre-not'] = genre_not
            
    return context

def _get_search_kwarg_type_map():
    type_map = {'year_min': int, 'year_max': int, 
                'runtime_min': int, 'runtime_max': int, 
                'keyword': bool,
                'black_and_white': bool, 'colour': bool,
                'digital': bool, 'physical': bool}
    return type_map

def _get_search_kwargs():
    """ Return list of kwarg names for search filters """
    return list(_get_search_kwarg_type_map().keys())

def _get_kwarg(kwargs, key):
    """ Get `key` from `kwargs` and cast value according to `_get_search_kwarg_type_map` """
    type_map = _get_search_kwarg_type_map()
    value = kwargs.get(key, None)
    if value is not None:
        t = type_map.get(key, None)
        if t is not None:
            value = t(value)
    return value

def _year_range() -> dict:
    """ Return dict with 'year_range_min' and 'year_range_max' keys from all VisionItems """
    return _get_range("year")
    
def _runtime_range() -> dict:
    """ Return dict with 'runtime_range_min' and 'runtime_range_max' keys from all VisionItems """
    return _get_range("runtime")

def _get_range(name, model_class=VisionItem) -> dict:
    """ Return dict with min and max values of `name` in the given `model_class` """
    values = set(model_class.objects.all().values_list(name, flat=True))
    dct = {f"{name}_range_min":min(values), f"{name}_range_max":max(values)}
    return dct

def _set_search_filters(context, request=None) -> dict:
    
    # add min and max values for the sliders (not the selected min and max vals)
    if 'year_range_min' not in context:
        context.update(_year_range())
    if 'runtime_range_min' not in context:
        context.update(_runtime_range())
    
    if 'year_min' not in context:
        context['year_min'] = context['year_range_min']
        context['year_max'] = context['year_range_max']
        
    if 'runtime_min' not in context:
        context['runtime_min'] = context['runtime_range_min']
        context['runtime_max'] = context['runtime_range_max']
        
    # colour/black and white and digital/physical: if unchecked, leave it. Otherwise, set checked
    tmp_dct = {}
    names = ['keyword', 'colour', 'black_and_white', 'digital', 'physical']
    for name in names:
        if context.get(name, False) is not False:
            tmp_dct[f'{name}_checked'] = True # assigning to context directly here didn't work
    context.update(tmp_dct)
            
    # have to manually get the background colour from style.css and pass it into the template
    # 0:neutral, 1:AND, 2:OR, 3:NOT
    genres = {}
    genre_text = ["\u2015", "AND", "OR", "NOT"]
    for g in Genre.objects.all():
        if g.name.lower() in context.get('genre-and', []):
            value = "1"
        elif g.name.lower() in context.get('genre-or', []):
            value = "2"
        elif g.name.lower() in context.get('genre-not', []):
            value = "3"
        else:
            value = "0"
        genres[g.name] = (value, genre_text[int(value)])
        context['genres'] = genres
    
    if 'all-genre-box-data' not in context and request is not None:
        values = set([value[0] for value in genres.values()])
        if len(values) == 1:
            value = values.pop()
        else:
            value = "0"
        context['all_genre_data'] = (request.GET.get('all-genre-box-data', value), genre_text[int(value)])
    
    return context

def _sort_search(item):
    return item.match, item.film.user_rating, item.film.imdb_rating

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
    """ Return list of words in string, as lower case, with non-alphnumeric characters removed """
    return [re.sub(r"\W", "", _s.lower()) for _s in s.split(" ") if _s]

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
    