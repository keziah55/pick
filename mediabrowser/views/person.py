from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import Person
from .search import set_search_filters
from .utils import filter_items_from_series, cast_vision_items
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE


def view_person(request, person):
    """Return sorted film list of person's films."""

    try:
        person = Person.objects.get(pk=person)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(f"<h1>No person found with id={person}</h1>")

    films = set(person.director.all()) | set(person.stars.all())
    films = filter_items_from_series(films)
    films = cast_vision_items(films)
    films = sorted(films, key=lambda film: (film.user_rating, film.imdb_rating), reverse=True)

    context = set_search_filters({})
    context["film_list"] = films
    context["filmlist_template"] = FILMLIST_TEMPLATE

    return render(request, INDEX_TEMPLATE, context)
