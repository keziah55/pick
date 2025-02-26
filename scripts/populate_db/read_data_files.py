from pathlib import Path
from decimal import Decimal
from typing import Any
from mediabrowser.models import VisionItem


def _make_visionitem_field_type_map():
    field_map = {}
    for field in VisionItem._meta.fields:
        field_class_name = field.__class__.__name__.lower()
        if field.name == "colour":
            continue
        if "integer" in field_class_name:
            field_map[field.name] = int
        elif "float" in field_class_name:
            field_map[field.name] = float
        elif "decimal" in field_class_name:
            field_map[field.name] = Decimal
        elif "bool" in field_class_name:
            field_map[field.name] = bool
    return field_map


_model_field_type_map = _make_visionitem_field_type_map()

_patch_to_model_map = {
    "media_id": "imdb_id",
    "image_url": "img",
}

_ext = [".avi", ".m4v", ".mkv", ".mov", ".mp4", ".wmv", ".webm"]

_sep = "\t"


def read_films_file(films_txt) -> list[Path]:
    with open(films_txt) as fileobj:
        files = [Path(file.strip()) for file in list(fileobj) if Path(file.strip()).suffix in _ext]
    return files


def read_patch_csv(patch_csv, key="filename", logger=None) -> dict[Path, dict[str, Any]]:
    """
    Return dict from csv file.

    Returns nested dict. Outer dict keys are filenames; values are dict of header: value pairs.
    """
    # make patch dict
    with open(patch_csv) as fileobj:
        header, *lines = fileobj.readlines()

    header = header.strip().split(_sep)
    try:
        key_idx = header.index(key)
    except ValueError:
        raise ValueError(f"No such item '{key}' in csv header: {header}")

    key_name = header.pop(key_idx)

    patch = {}
    for line in lines:
        values = line.split(_sep)
        key = values.pop(key_idx)
        if not key.strip():
            if logger is not None:
                logger.warning(f"Dropping '{key_name}' item {key=} when reading patch csv")
            continue
        elif key in patch:
            if logger is not None:
                logger.warning(f"'{key_name}' item {key=} already in patch dict. Skipping.")
            continue

        key = _format_patch_value(key.strip(), key_name)
        dct = {
            header[i]: _format_patch_value(value.strip(), header[i])
            for i, value in enumerate(values)
            if value
        }
        if "imdb_id" in dct:
            dct["media_id"] = dct.pop("imdb_id")
        # in case a file is entered twice in the csv, merge the two dicts
        current = patch.get(key, None)
        if current is None:
            patch[Path(key)] = dct
        else:
            current.update(dct)

    return patch


def make_combined_dict(films_txt=None, patch_csv=None) -> dict[Path, dict[str, Any]]:
    """Read `patch_csv` and add empty entries for any values in `films_txt` that are not in patch."""

    patch = read_patch_csv(patch_csv) if patch_csv is not None else {}
    if films_txt is not None:
        files = read_films_file(films_txt)
        films_dct = {film: {} for film in files if film not in patch}
        patch.update(films_dct)
    return patch


def read_physical_media_csv(media_csv) -> dict:  # list:
    """Return list of films that are available on physical media"""
    with open(media_csv) as fileobj:
        header, *lines = fileobj.readlines()

    header = header.lower().strip().split(_sep)
    title_idx = header.index("title")
    media_type_idx = header.index("media type")
    case_idx = header.index("case")
    slot_idx = header.index("slot")

    physical = {}
    for line in lines:
        line = line.lower()
        row = line.strip().split(_sep)
        if len(row) < len(header):
            break
        if row[media_type_idx].strip() == "film":
            # physical.append(row[title_idx])
            title, case, slot = [row[i] for i in [title_idx, case_idx, slot_idx]]
            physical[title] = _make_disc_index(case, slot)

    return physical


def _format_patch_value(value: str, name: str):
    """
    Given a value (and header name) from patch dict, cast to appropriate type.

    If string is the appropriate type, return `value` unaltered.

    Parameters
    ----------
    value
        Value read from patch csv.
    name
        Header name corresponding to value.

    Returns
    -------
    value
        `value` cast to appropriate type.

    """
    if name == "disc_index" and value:
        value = _make_disc_index(*value.split("."))
    else:
        key = _patch_to_model_map.get(name, name)

        if (cast_type := _model_field_type_map.get(key, None)) is not None:
            if cast_type == bool:
                match value.lower():
                    case "true":
                        value = True
                    case "false":
                        value = False
                    case _:
                        raise ValueError(f"Cannot cast '{value}' for field '{name}' to bool")
            else:
                value = cast_type(value)

    return value


def item_patch_equal(item, patch) -> bool:
    """Return True if all values in `patch` dict are the same as equivalent `item` fields."""
    for key, value in patch.items():
        item_key = _patch_to_model_map.get(key, key)
        db_value = getattr(item, item_key)
        if db_value != value:
            return False
    return True


def _make_disc_index(case, slot):
    return f"{int(case)}.{int(slot):03d}"
