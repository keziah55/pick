from pathlib import Path
from decimal import Decimal
from typing import Any
import logging
from mediabrowser.models import VisionItem, Person, Genre, Keyword, VisionSeries


logger = logging.getLogger("populate_db")


def _make_model_field_type_map() -> dict[str, dict[str, type]]:
    """For each model, make dict of field types."""
    model_map = {}
    models = [VisionItem, Person, Genre, Keyword, VisionSeries]
    for model in models:
        model_map[model.__name__] = field_map = {}
        for field in model._meta.fields:
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

    return model_map


_model_field_type_map = _make_model_field_type_map()

_patch_to_model_map = {
    "media_id": "imdb_id",
    "image_url": "img",
}

_ext = [".avi", ".m4v", ".mkv", ".mov", ".mp4", ".wmv", ".webm"]

_sep = "\t"  # csv item separator
_list_sep = ";"  # item list separator in csv field


def read_films_file(films_txt) -> list[Path]:
    with open(films_txt) as fileobj:
        files = [Path(file.strip()) for file in list(fileobj) if Path(file.strip()).suffix in _ext]
    return files


def read_patch_csv(patch_csv, key="filename") -> dict[Path, dict[str, Any]]:
    """
    Return dict from csv file.

    Returns nested dict. Outer dict keys are filenames; values are dict of header: value pairs.
    """
    patch = _read_csv_to_rows(
        patch_csv,
        key,
        VisionItem,
        list_keys=["alt_versions", "stars", "directors", "genre", "keyword"],
    )
    for key, dct in patch.items():
        if "imdb_id" in dct:
            patch[key]["media_id"] = dct.pop("imdb_id")
    return patch


def _read_csv_to_rows(
    csv_file: Path, key: str, model_class: type, list_keys: list[str] = None
) -> dict[Path, dict[str, Any]]:
    """
    Read csv file and return dict of rows.

    Parameters
    ----------
    csv_file
        Path to file to read.
    key
        Field (from csv header) to use a return dic key.
    model_class
        Model class that this data represents.
    list_keys
        Keys that (may) contain list of semicolon-separated values.

    Returns
    -------
    dict[Path, dict[str, Any]]
        Outer dict uses given `key`; inner dict pairs each remaining header field with the value
        for each row.

    """
    if not csv_file.exists():
        raise FileNotFoundError(f"csv file '{csv_file}' does not exist")

    text = csv_file.read_text()
    return _csv_to_rows(text, key=key, model_class=model_class, list_keys=list_keys)


def _csv_to_rows(
    csv_data: str, key: str, model_class: type, list_keys: list[str] = None
) -> dict[Path, dict[str, Any]]:
    """
    Read csv file and return dict of rows.

    Parameters
    ----------
    csv_data
        Data from csv file
    key
        Field (from csv header) to use a return dic key.
    model_class
        Model class that this data represents.
    list_keys
        Keys that (may) contain list of semicolon-separated values.

    Returns
    -------
    dict[Path, dict[str, Any]]
        Outer dict uses given `key`; inner dict pairs each remaining header field with the value
        for each row.

    """
    header, *lines = [line for line in csv_data.split("\n") if line]

    header = header.strip().split(_sep)
    try:
        key_idx = header.index(key)
    except ValueError:
        raise ValueError(f"No such item '{key}' in csv header: {header}")

    key_name = header.pop(key_idx)

    if list_keys is None:
        list_keys = []

    patch = {}
    for line in lines:
        values = line.split(_sep)

        key = values.pop(key_idx)
        if not key.strip():
            logger.warning(f"Dropping '{key_name}' item {key=} when reading csv")
            continue
        elif key in patch:
            logger.warning(f"'{key_name}' item {key=} already in dict. Skipping.")
            continue

        key = _format_patch_value(key.strip(), key_name, model_class)
        dct = {}
        for i, value in enumerate(values):
            if not value:
                continue

            if header[i] in list_keys:
                value = [
                    _format_patch_value(val.strip(), header[i], model_class)
                    for val in value.split(_list_sep)
                ]
            else:
                value = _format_patch_value(value.strip(), header[i], model_class)

            dct[header[i]] = value

        # in case a file is entered twice in the csv, merge the two dicts
        current = patch.get(key, None)
        if current is None:
            patch[key] = dct
        else:
            current.update(dct)

    return patch


def make_combined_dict(films_txt=None, patch_csv=None) -> dict[Path, dict[str, Any]]:
    """Read `patch_csv` and add empty entries for any values in `films_txt` that are not in patch."""

    patch = read_patch_csv(patch_csv) if patch_csv is not None else {}
    if films_txt is not None:
        files = read_films_file(films_txt)
        # films_dct = {film: {} for film in files if film not in patch}
        films_dct = {film: None for film in files if film not in patch}
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


def _format_patch_value(value: str, name: str, model_class: type):
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
    model_name = model_class.__name__
    if model_name not in _model_field_type_map:
        raise ValueError(
            f"Unknown model '{model_name}'. "
            f"Valid values are: {', '.join(_model_field_type_map.keys())}"
        )
    else:
        field_map = _model_field_type_map[model_name]

    if not value:
        return value

    match name:
        case "disc_index":
            value = _make_disc_index(*value.split("."))
        case "filename":
            value = Path(value)
        case _:
            key = _patch_to_model_map.get(name, name)

            if (cast_type := field_map.get(key, None)) is not None:
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

    if isinstance(value, str):
        value = value.strip()

    return value


def item_patch_equal(item, patch) -> bool:
    """Return True if all values in `patch` dict are the same as equivalent `item` fields."""
    for key, value in patch.items():
        item_key = _patch_to_model_map.get(key, key)
        db_value = getattr(item, item_key)

        if key == "colour":
            # colour is string in patch/IMDb data, but bool in DB
            if not isinstance(value, bool):
                value = any("color" in item.lower() for item in value)

        if hasattr(db_value, "all"):
            db_value = db_value.all()
            if len(db_value) == 0:
                return False
            if hasattr(db_value[0], "filename"):
                db_value = [item.filename for item in db_value]
            else:
                db_value = [item.name for item in db_value]

        if db_value != value:
            return False
    return True


def _make_disc_index(case, slot):
    return f"{int(case)}.{int(slot):03d}"


def read_alias_csv(alias_csv: Path) -> dict[Path, dict[str, Any]]:
    """Return dict of name:alias pairs."""
    return _read_csv_to_rows(alias_csv, key="imdb_id", model_class=Person)


def read_series_csv(series_csv: Path) -> dict[Path, dict[str, Any]]:
    dct = _read_csv_to_rows(
        series_csv, key="series_name", model_class=VisionSeries, list_keys=["titles", "items"]
    )

    for name, data in dct.items():
        if "items" in data:
            dct[name]["items"] = [int(pk) for pk in data["items"]]

    return dct
