from django.shortcuts import render
from django.http import HttpResponse

from .models import MediaItem

import random

# def index(request):
#     items = MediaItem.objects.all()
#     num = len(items)
#     idx = random.randint(0, num-1)
#     item = items[idx]
#     output = f"{item}"
#     return HttpResponse(output)

def index(request):
    # see if the `request` object has a 'search' item
    try:
        search = request.GET['search']
    # if not, use empty string
    except:
        search = ''
    
    # search title, artist and year fields for the `search` string
    results = MediaItem.objects.filter(title__icontains=search)
    # merge the filtered datasets
    # results = a1 | a2 | a3
    # sort albums by rating, in descending order
    # sorted_album_list = results.order_by('-rating')
    
    # make string to display in search bar
    if search:
        search_placeholder = "Showing results for: '{}'".format(search)
    else:
        search_placeholder = 'Search...'
    
    # args to be substituted into the templates    
    context = {'film_list':results,
               'search_placeholder':search_placeholder}
    
    return render(request, 'pick/index.html', context)