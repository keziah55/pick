from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from ..models import VisionItem, MediaItem
from .search import set_search_filters
from .templates import INDEX_TEMPLATE, FILMLIST_TEMPLATE


def view_visionitem(request, pk):
    """Return view of VisionItem."""
    # item = _get_item(pk, VisionItem)

    context = set_search_filters({})

    try:
        item = VisionItem.objects.get(pk=pk)
    except ObjectDoesNotExist:
        try:
            item = MediaItem.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"<h1>No media item found with id={pk}</h1>")
        else:
            items = [_get_item(child.pk, VisionItem) for child in item.children.all()]

    else:
        items = [item]

    context["film_list"] = items
    context["filmlist_template"] = FILMLIST_TEMPLATE

    return render(request, INDEX_TEMPLATE, context)


def _get_item(pk, model_cls):
    """Return item of model class `model_cls` with given primary key."""
    try:
        item = model_cls.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(f"<h1>No {model_cls.__name__} found with id={pk}</h1>")
    else:
        return item
