from django.shortcuts import render
from django.http import HttpResponse

from .models import VisionItem, MediaSeries, Genre, Keyword, Person

from itertools import chain
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
    if (year_min:=kwargs.get('year_min', None)) is not None and (year_max:=kwargs.get('year_max', None)) is not None:
        filter_kwargs['year__range'] = (int(year_min), int(year_max))
    if (runtime_min:=kwargs.get('runtime_min', None)) is not None and (runtime_max:=kwargs.get('runtime_max', None)) is not None:
        filter_kwargs['runtime__range'] = (int(runtime_min), int(runtime_max))
    
    # always search VisionItem by title
    results = list(VisionItem.objects.filter(title__icontains=search_str, **filter_kwargs))
    
    if search_str:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__icontains=search_str)
        for person in persons:
            # get person's films, applying filters
            results += [film for film in person.stars.filter(**filter_kwargs) if film not in results]
            results += [film for film in person.director.filter(**filter_kwargs) if film not in results]
            # results += list(chain(person.stars.filter(**filter_kwargs), person.director.filter(**filter_kwargs)))
        keywords = Keyword.objects.filter(name__icontains=search_str)
        for keyword in keywords:
            results += [film for film in keyword.visionitem_set.filter(**filter_kwargs) if film not in results]
            # for film in keyword.visionitem_set.filter(**filter_kwargs):
                # if film not in results:
                    # results.append(film)
                    
    ## to get all items with genre 'g'
    ## g.VisionItem_set.all()
    
    # make string to display in search bar
    if search_str:
        search_placeholder = "Showing results for: '{}'".format(search_str)
    else:
        search_placeholder = 'Search...'
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_placeholder':search_placeholder}
    return context

def _get_context_from_request(request) -> dict:
    """ Try to get year and runtime min and max from `request` """
    context = {}
    
    for key in ['year_min', 'year_max', 'runtime_min', 'runtime_max']:
        try:
            value = request.GET[key]
            print(f"get '{key}' = {value}")
        except:
            print(f"could not get value for '{key}'")
            pass
        else:
            context[key] = value
            
    return context

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