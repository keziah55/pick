from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem
from .search import set_search_filters
from .templates import INDEX_TEMPLATE, FILM_TEMPLATE
import re


def set_user_rating(request):

    template = INDEX_TEMPLATE

    submitter = request.POST["submitter"]
    m = re.match(r"star-(?P<rating>\d+)-(?P<pk>\d+)", submitter)
    pk, rating = [int(m.group(name)) for name in ["pk", "rating"]]
    try:
        film = VisionItem.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(f"<h1>No film found with id={pk}</h1>")
    film.user_rating = rating
    film.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        template = FILM_TEMPLATE
        context = {"film": film}
    else:
        context = set_search_filters({})

    return render(request, template, context)
