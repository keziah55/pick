from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem, VisionSeries, MediaItem
from .utils import set_search_filters, get_filter_kwargs, get_context_from_request, cast_vision_item
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE, FILM_TEMPLATE
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

    if (parent:=film.parent_series) is not None:
        # TODO keep propagating up if parent has parent
        # parent user_rating is max of members
        if rating != parent.user_rating and parent.media_type == MediaItem.SERIES:
            parent = VisionSeries.objects.get(pk=parent.pk)
            parent.user_rating = max(
                cast_vision_item(member).user_rating for member in parent.members.all()
            )
            parent.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        template = FILM_TEMPLATE
        context = {"film": film}
    else:
        context = set_search_filters({})

    return render(request, template, context)


def view_user_rating(request, rating):

    template = INDEX_TEMPLATE

    context = get_context_from_request(request)

    filter_kwargs, _, _ = get_filter_kwargs(**context)

    items = VisionItem.objects.filter(user_rating__exact=rating, **filter_kwargs)

    context["film_list"] = list(items)
    context = set_search_filters(context, request)

    context["filmlist_template"] = FILMLIST_TEMPLATE
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        template = FILMLIST_TEMPLATE

    return render(request, template, context)
