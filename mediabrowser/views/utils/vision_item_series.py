from typing import Union
import itertools

from ...models import VisionItem, VisionSeries, MediaItem
from django.core.exceptions import ObjectDoesNotExist


def get_top_level_parent(item: Union[VisionItem, VisionSeries]) -> Union[VisionItem, VisionSeries]:
    """
    Recurse up through `parent_series` until there is no parent.

    Return the final parent-less item.

    Parameters
    ----------
    item : Union[VisionItem, VisionSeries]
        VisionItem or VisionSeries to find top level parent of.

    Returns
    -------
    Union[VisionItem, VisionSeries]
        Return the VisionItem or VisionSeries with no parent.

    """
    if item.parent_series is None:
        return item

    while True:
        parent = item.parent_series
        if parent is None:
            break
        else:
            item = parent
    return item


def is_single_item_in_series(item: Union[VisionItem, VisionSeries]) -> bool:
    """
    Return True if all parents of `item` contain only one member.

    If `item` has no parent series, this returns True.
    """
    if item.parent_series is None:
        return True

    while True:
        parent = item.parent_series
        if parent is None:
            break
        elif len(parent.members.all()) > 1:
            return False
        else:
            item = parent

    return True


_vision_types = {MediaItem.FILM: VisionItem, MediaItem.SERIES: VisionSeries}


def cast_vision_item(item: MediaItem, database="default") -> Union[VisionItem, VisionSeries]:
    """
    If `item` is a FILM or SERIES media type, get item of correct model class.

    Parameters
    ----------
    item
        MediaItem to cast.

    Raises
    ------
    ValueError
        If media type of `item` is not FILM or SERIES.

    Returns
    -------
    Union[VisionItem, VisionSeries]
        Item as correct model instance.

    """
    t = item.media_type
    if (model_cls := _vision_types.get(t), None) is not None:
        return model_cls.objects.using(database).get(pk=item.pk)
    else:
        raise ValueError(
            f"cast_vision_item can only operate on FILM or SERIES media types, not {t}"
        )


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


def get_media_item_by_pk(pk: int, database="default")-> Union[VisionItem, VisionSeries]:
    """Return either `VisionItem` or `VisionSeries` with the given `pk."""
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
