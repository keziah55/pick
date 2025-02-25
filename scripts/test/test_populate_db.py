from pathlib import Path

import pytest

from ..populate_db import PopulateDatabase
from ..populate_db.read_data_files import read_patch_csv, make_combined_dict


def test_combine_patch_films_list(
    films_txt, patch_csv, expected_patch_filenames, expected_films_filenames
):

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


@pytest.mark.django_db(databases=["db_test"], transaction=True)
def test_populate_db(films_txt, patch_csv, expected_patch_filenames, expected_films_filenames):
    print()

    pop_db = PopulateDatabase(quiet=False, database="db_test")
    n = pop_db.update(films_txt=films_txt, patch_csv=patch_csv)

    assert n == len(expected_films_filenames) + len(expected_patch_filenames)
