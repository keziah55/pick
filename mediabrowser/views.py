from django.shortcuts import render
from django.http import HttpResponse

from .models import VisionItem, MediaSeries, Genre, Keyword, Person

from itertools import chain

def index(request):
    # see if the `request` object has a 'search' item
    try:
        search = request.GET['search']
    # if not, use empty string
    except:
        search = ''
        
    # TODO limit number of results
    # i.e. paging
    
    # search title, director, stars and keywords fields
    results = list(VisionItem.objects.filter(title__icontains=search))
    if search:
        # only search people and keywords if given a search string
        persons = Person.objects.filter(name__icontains=search)
        for person in persons:
            results += list(chain(person.stars.all(), person.director.all()))
        keywords = Keyword.objects.filter(name__icontains=search)
        for keyword in keywords:
            for film in keyword.visionitem_set.all():
                if film not in results:
                    results.append(film)
    
    ## to get all items with genre 'g'
    ## g.VisionItem_set.all()
    
    # make string to display in search bar
    if search:
        search_placeholder = "Showing results for: '{}'".format(search)
    else:
        search_placeholder = 'Search...'
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_placeholder':search_placeholder}
    
    return render(request, 'mediabrowser/index.html', context)