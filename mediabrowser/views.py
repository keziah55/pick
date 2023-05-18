from django.shortcuts import render
from django.http import HttpResponse

from .models import VisionItem, MediaSeries, Genre, Keyword, Person

from itertools import chain

def index(request):
    # see if the `request` object has a 'search' item
    try:
        search_str = request.GET['search']
    # if not, use empty string
    except:
        search_str = ''
        
    context = _get_context_from_request(request)
    context.update(_search(search_str))
    
    if not search_str:
        context.update(_year_range())
        context.update(_runtime_range())
        
    return render(request, 'mediabrowser/index.html', context)
    
def search(request, search_str):
    context = _get_context_from_request(request)
    context.update(_search(search_str))
    return render(request, 'mediabrowser/index.html', context)

def _search(search_str) -> dict:
    """ 
    Search VisionItems for `search_str` 
    
    If `search_str` is empty string, return all VisionItems. 
    Otherwise, also search Person and Keyword tables.
    """
    # search title, director, stars and keywords fields
    results = list(VisionItem.objects.filter(title__icontains=search_str))
    if search_str:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__icontains=search_str)
        for person in persons:
            results += list(chain(person.stars.all(), person.director.all()))
        keywords = Keyword.objects.filter(name__icontains=search_str)
        for keyword in keywords:
            for film in keyword.visionitem_set.all():
                if film not in results:
                    results.append(film)
    
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
    """ Try to get year and runtime min and max from request """
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
    """ Return dict with 'year_min' and 'year_max' keys from all VisionItems """
    return _get_range("year")
    
def _runtime_range() -> dict:
    """ Return dict with 'runtime_min' and 'runtime_max' keys from all VisionItems """
    return _get_range("runtime")

def _get_range(name, model_class=VisionItem) -> dict:
    """ Return dict with min and max values of `name` in the given `model_class` """
    values = set(model_class.objects.all().values_list(name, flat=True))
    dct = {f"{name}_min":min(values), f"{name}_max":max(values)}
    return dct