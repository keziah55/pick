from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.list import ListView
from django.db.models import Q
from .models import VisionItem, MediaSeries, Genre, Keyword, Person
import os.path
import re

from pprint import pprint

def index(request, template='mediabrowser/index.html', filmlist_template='mediabrowser/filmlist.html'):
    # see if the `request` object has a 'search' item
    try:
        search_str = request.GET['search']
    # if not, use empty string
    except:
        search_str = ''
        
    context = _get_context_from_request(request)
    
    search_results = _search(search_str, **context)
    context.update(search_results)
    
    context = _set_search_filters(context, request)
    
    context['filmlist_template'] = filmlist_template
    if request.headers.get('x-requested-with') == 'XMLHttpRequest': 
        template = filmlist_template
    
    return render(request, template, context)
    
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
    print(f"{search_keywords=}")
            
    genre_include = set(kwargs.get('genre-include', []))
    genre_exclude = set(kwargs.get('genre-exclude', []))
            
    results = []
    
    # always search VisionItem by title
    results = [film for film in VisionItem.objects.filter(
                 Q(title__icontains=search_str) | Q(alt_title__icontains=search_str), 
                 **filter_kwargs)
               if _check_include_film(film, results, genre_include, genre_exclude)]
    
    if search_str:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__icontains=search_str) | Person.objects.filter(alias__icontains=search_str)
        for person in persons:
            # get person's films, applying filters
            results += [film for film in person.stars.filter(**filter_kwargs) 
                        if _check_include_film(film, results, genre_include, genre_exclude)]
            results += [film for film in person.director.filter(**filter_kwargs) 
                        if _check_include_film(film, results, genre_include, genre_exclude)]
        if search_keywords:
            keywords = Keyword.objects.filter(name__icontains=search_str)
            for keyword in keywords:
                results += [film for film in keyword.visionitem_set.filter(**filter_kwargs) 
                            if _check_include_film(film, results, genre_include, genre_exclude)]
    
    results = sorted(results, key=_sort_rating, reverse=True)
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_str':search_str}
    
    return context

def _check_include_film(film, results, genre_include, genre_exclude=None) -> bool:
    """ 
    Return True if `film` not already in `results` and any of its genres are in `genres` set.
    
    Parameters
    ----------
    film : VisionItem
        Film to check
    results : list
        List of VisionItems
    genre_include : set, optional
        Set of genre names to include (as lower case strings)
    genre_exclude : set, optional
        Set of genre names to exclude (as lower case strings)
    """
    film_is_new = film not in results
    film_genres = set([g.name.lower() for g in film.genre.all()])
    
    if genre_include is None:
        genre_include = set()
    if genre_exclude is None:
        genre_exclude = set()
    
    if len(genre_include) == 0 and len(genre_exclude)==0:
        return film_is_new
    
    # include if no include genres specified or if all include genres are in film_genres
    include = True if len(genre_include)==0 else genre_include.issubset(film_genres)
    # exclude if there's any overlap in genres
    not_exclude = True if len(genre_exclude)==0 else genre_exclude.isdisjoint(film_genres)
    
    return film_is_new and include and not_exclude

def _get_context_from_request(request) -> dict:
    """ Try to get year and runtime min and max from `request` """
    context = {}
    
    for key, value in request.GET.items():
        if key in _get_search_kwargs():
            context[key] = value
        elif key.startswith('genre-'):
            value = int(value)
            if value == 1:
                k = 'genre-include'
            elif value == 2:
                k = 'genre-exclude'
            else:
                # do nothing for neutral filter
                continue
            if k not in context:
                context[k] = []
            if (m:=re.match(r"genre-(?P<genre>.+)-data", key)) is not None:
                context[k].append(m.group('genre'))
                
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
    genres = {}
    genre_colours = _get_multistate_colours()
    for g in Genre.objects.all():
        if g.name.lower() in context.get('genre-include', []):
            value = "1"
            colour = genre_colours['include']
        elif g.name.lower() in context.get('genre-exclude', []):
            value = "2"
            colour = genre_colours['exclude']
        else:
            value = "0"
            colour = genre_colours['neutral']
        genres[g.name] = (value, colour)
        context['genres'] = genres
    
    if 'all-genre-box-data' not in context and request is not None:
        values = set([value[0] for value in genres.values()])
        if len(values) == 1:
            value = values.pop()
            if value == "1":
                colour = genre_colours['include']
            elif value == "2":
                colour = genre_colours['exclude']
        else:
            value = "0"
            colour = genre_colours['neutral']
        context['all_genre_data'] = (request.GET.get('all-genre-box-data', value), colour)
    
    return context

def _get_multistate_colours() -> dict:
    """ Get dict of include, exclude and neutral colours from style.css """
    p = os.path.join(os.path.dirname(__file__), 'static', 'mediabrowser', 'css', 'style.css')
    with open(p) as fileobj:
        text = fileobj.read()
    dct = {}
    keys = ['include', 'exclude', 'neutral']
        
    if (m:=re.search(r":root *\{(?P<content>.*?)\}", text, re.DOTALL)) is not None:
        for line in m.group('content').split("\n"):
            for key in keys:
                if (m2:=re.match(f"\s*--{key}-color: (?P<colour>#\w+)", line)) is not None:
                    dct[key] = m2.group('colour')
    return dct
        
def _sort_rating(item):
    return item.user_rating, item.imdb_rating
