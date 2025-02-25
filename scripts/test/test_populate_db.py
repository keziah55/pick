import pytest

from ..populate_db import PopulateDatabase
from ..populate_db.read_data_files import read_patch_csv, make_combined_dict


def test_combine_patch_films_list(films_txt, patch_csv):

    expected_patch_filenames = [
        "Before_Midnight.mkv",
        "Before_Sunrise.mkv",
        "Before_Sunset.mkv",
        "Juste Avant La Nuit.mkv",
        "the nightmare before christmas",
        "before the devil knows you're dead",
        "Men_in_Black_2.mkv",
        "Men_in_Black_3.mkv",
        "Men_In_Black.mkv",
        "Lord of the Rings The Fellowship of the Rings.mkv",
        "Lord of the Rings The Two Towers.mkv",
        "Lord of the Rings The Return of the King.mkv",
        "Lord of the Rings The Fellowship of the Rings Extended.mkv",
        "Lord of the Rings The Two Towers Extended.mkv",
        "Lord of the Rings The Return of the King Extended.mkv",
        "Skyfall.mkv",
        "spectre",
        "No_Time_to_Die.mkv",
        "Koyaanisqatsi.mkv",
        "Powaqqatsi.mkv",
        "Die Hard.mkv",
    ]
    expected_films_filenames = ["Drive.mkv"]

    combined_dct = make_combined_dict(films_txt, patch_csv)
    assert set(combined_dct.keys()) == set(expected_patch_filenames) | set(expected_films_filenames)

    for fname in expected_patch_filenames:
        assert len(combined_dct[fname]) > 0

    for fname in expected_films_filenames:
        assert len(combined_dct[fname]) == 0

    patch_dct = make_combined_dict(None, patch_csv)
    assert set(patch_dct.keys()) == set(expected_patch_filenames)

    films_dct = make_combined_dict(films_txt, None)
    assert films_dct == {fname: {} for fname in expected_films_filenames}

    assert make_combined_dict(None, None) == {}
