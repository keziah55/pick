import pytest

from ..populate_db import PopulateDatabase

def test_combine_patch_films_list(films_txt, patch_csv):
    pop_db = PopulateDatabase()

    combined_dct = pop_db._make_combined_dict(films_txt, patch_csv)
    print()
    print(combined_dct)