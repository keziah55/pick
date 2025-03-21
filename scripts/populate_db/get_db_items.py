import itertools

from django.core.exceptions import ObjectDoesNotExist
from mediabrowser.models import VisionItem, VisionSeries


def get_derived_instance(item, database="default"):
    try:
        item = VisionSeries.objects.using(database).get(pk=item.pk)
    except ObjectDoesNotExist:
        try:
            item = VisionItem.objects.using(database).get(pk=item.pk)
        except ObjectDoesNotExist:
            msg = f"Item {item.pk} {item} is neither a VisionSeries nor a VisionItem."
            raise RuntimeError(msg)
    return item


def get_item(pk, database="default"):
    try:
        item = VisionItem.objects.using(database).get(pk=pk)
    except ObjectDoesNotExist:
        try:
            item = VisionSeries.objects.using(database).get(pk=pk)
        except ObjectDoesNotExist:
            raise ValueError(f"No VisionItem or VisionSeries found for {pk}")
    return item


def filter_visionitem_visionseries(database="default", **kwargs) -> list[VisionItem | VisionSeries]:
    """Call `filter` on both `VisionItem` and `VisionSeries` with the given kwargs."""
    results = [
        model_cls.objects.using(database).filter(**kwargs)
        for model_cls in [VisionItem, VisionSeries]
    ]
    return list(itertools.chain(*results))
