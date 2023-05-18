from django.shortcuts import render
from django.http import HttpResponse

from .models import VisionItem, MediaSeries, Genre, Keyword, Person

import re
from pprint import pprint

def index(request):
    # see if the `request` object has a 'search' item
    try:
        search_str = request.GET['search']
    # if not, use empty string
    except:
        search_str = ''
        
    context = _get_context_from_request(request)
    
    search_results = _search(search_str, **context)
    context.update(search_results)
    
    # add min and max values for the sliders (not the selected min and max vals)
    context.update(_year_range())
    context.update(_runtime_range())
    
    if 'year_min' not in context:
        context['year_min'] = context['year_range_min']
        context['year_max'] = context['year_range_max']
        
    if 'runtime_min' not in context:
        context['runtime_min'] = context['runtime_range_min']
        context['runtime_max'] = context['runtime_range_max']
        
    # colour/black and white: if unchecked, leave it. otheriwse, set checked
    if context.get('colour', None) is not False:
        context['colour_checked'] = True
        
    if context.get('black_and_white', None) is not False:
        context['black_and_white_checked'] = True
        
    genres = {g.name:g.name.lower() in context.get('genres', []) for g in Genre.objects.all()}
    if all([value is False for value in genres.values()]):
        # don't allow all genres unchecked
        for key in genres:
            genres[key] = True
    context['genres'] = genres
    
    if 'all_genre_checked' not in context:
        all_genres = all(genres.values()) 
        context['all_genre_checked'] = request.GET.get('all-genre-box', all_genres)
    
    return render(request, 'mediabrowser/index.html', context)
    
def search(request, search_str):
    context = _get_context_from_request(request)
    search_results = _search(search_str, **context)
    context.update(search_results)
    return render(request, 'mediabrowser/index.html', context)

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
            
    genres = set(kwargs.get('genres', []))
            
    results = []
    
    # always search VisionItem by title
    results = [film for film in VisionItem.objects.filter(title__icontains=search_str, **filter_kwargs)
               if _check_include_film(film, results, genres)]
    
    if search_str:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__icontains=search_str)
        for person in persons:
            # get person's films, applying filters
            results += [film for film in person.stars.filter(**filter_kwargs) 
                        if _check_include_film(film, results, genres)]
            results += [film for film in person.director.filter(**filter_kwargs) 
                        if _check_include_film(film, results, genres)]
        keywords = Keyword.objects.filter(name__icontains=search_str)
        for keyword in keywords:
            results += [film for film in keyword.visionitem_set.filter(**filter_kwargs) 
                        if _check_include_film(film, results, genres)]
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_str':search_str}
    return context

def _check_include_film(film, results, genres) -> bool:
    """ 
    Return True if `film` not already in `results` and any of its genres are in `genres` set.
    
    Parameters
    ----------
    film : VisionItem
        Film to check
    results : list
        List of VisionItems
    genres : set
        Set of genre names (as lower case strings)
    """
    film_genres = set([g.name.lower() for g in film.genre.all()])
    not_disjoint = True if len(genres)==0 else not genres.isdisjoint(film_genres)
    return film not in results and not_disjoint

def _get_context_from_request(request) -> dict:
    """ Try to get year and runtime min and max from `request` """
    context = {}
    
    for key, value in request.GET.items():
        if key in _get_search_kwargs():
            context[key] = value
        elif key.startswith('genre-'):
            if 'genres' not in context:
                context['genres'] = []
            if (m:=re.match(r"genre-(?P<genre>.+)", key)) is not None:
                context['genres'].append(m.group('genre'))
    return context

def _get_search_kwarg_type_map():
    type_map = {'year_min':int, 'year_max':int, 'runtime_min':int, 'runtime_max':int, 
                'black_and_white':bool, 'colour':bool}
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