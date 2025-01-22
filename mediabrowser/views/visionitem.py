from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem, VisionSeries
from .search import set_search_filters
from .utils import cast_vision_item
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE


def view_visionitem(request, pk):
    """Return view of VisionItem."""

    context = set_search_filters({})

    try:
        item = VisionItem.objects.get(pk=pk)
    except ObjectDoesNotExist:
        try:
            item = VisionSeries.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"<h1>No media item found with id={pk}</h1>")
        else:
            items = [cast_vision_item(child) for child in item.members.all()]

    else:
        items = [item]

    context["film_list"] = items
    context["filmlist_template"] = FILMLIST_TEMPLATE

    return render(request, INDEX_TEMPLATE, context)
