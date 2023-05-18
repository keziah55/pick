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
        
    context = _search(search_str)
    
    years = set(VisionItem.objects.all().values_list('year', flat=True))
    runtimes = set(VisionItem.objects.all().values_list('runtime', flat=True))
    
    context['year_min'] = min(years)
    context['year_max'] = max(years)
    context['runtime_min'] = min(runtimes)
    context['runtime_max'] = max(runtimes)
    
    return render(request, 'mediabrowser/index.html', context)
    
def search(request, search_str):
    context = _search(search_str)
    return render(request, 'mediabrowser/index.html', context)

def _search(search_str):
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