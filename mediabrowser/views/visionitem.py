from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem, MediaItem
from .search import set_search_filters
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE, SERIESLIST_TEMPLATE

from pprint import pprint


def view_visionitem(request, pk):
    """Return view of VisionItem."""
    item = _get_item(pk, VisionItem)

    context = set_search_filters({})
    context["film_list"] = [item]
    context["filmlist_template"] = FILMLIST_TEMPLATE

    return render(request, INDEX_TEMPLATE, context)


def view_mediaitem(request, pk):
    """Return view of MediaItem."""
    item = _get_item(pk, MediaItem)

    # return children as VisionItems, not MediaItems
    items = [_get_item(child.pk, VisionItem) for child in item.children.all()]

    context = set_search_filters({})
    # context["series_item"] = item
    # context["series_members"] = items
    # context["serieslist_template"] = SERIESLIST_TEMPLATE
    context["film_list"] = items
    context["filmlist_template"] = FILMLIST_TEMPLATE


    pprint(context)

    return render(request, INDEX_TEMPLATE, context)


def _get_item(pk, model_cls):
    """Return item of model class `model_cls` with given primary key."""
    try:
        item = model_cls.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(f"<h1>No {model_cls.__name__} found with id={pk}</h1>")
    else:
        return item
