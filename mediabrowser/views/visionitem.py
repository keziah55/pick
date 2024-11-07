from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem
from .search import set_search_filters
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE


def view_visionitem(request, pk):
    """Return view of VisionItem."""

    try:
        item = VisionItem.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(f"<h1>No VisionItem found with id={pk}</h1>")

    context = set_search_filters({})
    context["film_list"] = [item]
    context["filmlist_template"] = FILMLIST_TEMPLATE

    return render(request, INDEX_TEMPLATE, context)
