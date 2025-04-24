import pytest

from pathlib import Path

from ..populate_db import PopulateDatabase
from ..populate_db.read_data_files import (
    read_patch_csv,
    read_alias_csv,
    read_series_csv,
    make_combined_dict,
)
from ..populate_db.media_info import MediaInfoProcessor
from ..populate_db.person_info import make_personinfo
from imdb import Cinemagoer
from mediabrowser.models import VisionItem, VisionSeries, Person


DATABASE = "db_test"


def test_combine_patch_films_list(
    films_txt, patch_csv, expected_patch_filenames, expected_films_filenames
):

    combined_dct = make_combined_dict(films_txt, patch_csv)
    assert set(combined_dct.keys()) == set(expected_patch_filenames) | set(expected_films_filenames)

    for fname in expected_patch_filenames:
        assert len(combined_dct[fname]) > 0

    for fname in expected_films_filenames:
        assert combined_dct[fname] is None

    patch_dct = make_combined_dict(None, patch_csv)
    assert set(patch_dct.keys()) == set(expected_patch_filenames)

    films_dct = make_combined_dict(films_txt, None)
    assert films_dct == {fname: None for fname in expected_films_filenames}

    assert make_combined_dict(None, None) == {}


@pytest.mark.django_db(databases=[DATABASE], transaction=True)
def test_populate_db(
    films_txt,
    patch_csv,
    physical_media_csv,
    alias_csv,
    series_csv,
    expected_patch_filenames,
    expected_films_filenames,
    expected_imdb_ids,
    monkeypatch,
):
    print()

    read_patch_csv_orig = read_patch_csv

    def patch_no_disc_index(patch_csv):
        # remove disc indexes, so we can check that they're added from physical media csv
        patch = read_patch_csv_orig(patch_csv)

        for file in patch.keys():
            patch[file].pop("disc_index", None)

        return patch

    from ..populate_db import read_data_files

    monkeypatch.setattr(read_data_files, "read_patch_csv", patch_no_disc_index)

    pop_db = PopulateDatabase(
        physical_media=physical_media_csv, alias_csv=alias_csv, quiet=False, database=DATABASE
    )
    n = pop_db.populate_items(films_txt=films_txt, patch_csv=patch_csv)

    assert n == len(expected_films_filenames) + len(expected_patch_filenames)

    expected_created_items = {"visionitem": 24, "genre": 16, "person": 1507, "keywords": 0}

    # for key, expected_count in expected_created_items.items():
    #     assert pop_db._created_item_count[key] == expected_count

    # check that info from physical media csv was applied correctly
    patch = read_patch_csv_orig(patch_csv)
    for file, info in patch.items():
        if info.get("disc_index", "") != "":
            item = VisionItem.objects.using(DATABASE).get(filename=str(file))
            assert (
                item.disc_index == info["disc_index"]
            ), f"{file=}, expected disc index {info['disc_index']}, got {item.disc_index}"

    people = Person.objects.using(DATABASE).filter(name="Charles Chaplin")
    assert len(people) == 1
    assert people[0].alias == "Charlie Chaplin"

    # check all items are correct
    items = VisionItem.objects.using(DATABASE).all()
    assert len(items) == 24
    for item in items:
        assert expected_imdb_ids[item.filename] == item.imdb_id

    n = pop_db.populate_items(films_txt=films_txt, patch_csv=patch_csv)
    assert n == 0

    # series
    n = pop_db.populate_series(series_csv)
    assert n == 6

    series = VisionSeries.objects.using(DATABASE).all()
    assert len(series) == 6
    for s in series:
        assert len(s.members.all()) > 0

    expected_series = {
        "james bond": ["skyfall", "spectre", "no time to die"],
        "before trilogy": ["before sunrise", "before sunset", "before midnight"],
    }
    for series_title, member_titles in expected_series.items():
        series = VisionSeries.objects.using(DATABASE).filter(title__iexact=series_title)
        assert len(series) == 1
        assert [item.title.lower() for item in series[0].members.all()] == member_titles

    n = pop_db.populate_series(series_csv)
    assert n == 0


@pytest.mark.parametrize("person", ["Charles Chaplin", "0000122", "122"])
def test_alias(alias_csv, person):
    dct = read_alias_csv(alias_csv)

    cinemagoer = Cinemagoer()

    person_info = make_personinfo(person, cinemagoer, dct)
    assert person_info.name == "Charles Chaplin"
    assert person_info.alias == "Charlie Chaplin"
    assert person_info.id == "0000122"


@pytest.mark.parametrize(
    "title,expected_id",
    [
        ("Thelma and Louise", "0103074"),
        ("Fantastic_Mr_Fox", "0432283"),
        ("The Man Who Knew Too Much (1934)", "0025452"),
        ("Willy Wonka and the Chocolate Factory", "0067992"),
    ],
)
def test_get_from_imdb(title, expected_id):
    media_info_proc = MediaInfoProcessor()

    movie = media_info_proc._get_movie_from_imdb(title)
    assert movie.getID() == expected_id


def test_read_patch_csv(data_dir):
    patch_csv = data_dir.joinpath("patch_alt_versions.csv")
    patch = read_patch_csv(patch_csv)
    assert patch[Path("Blade Runner.mkv")]["alt_versions"] == [
        "blade_runner_directors_cut.mkv",
        "blade_runner_theatrical_cut.mkv",
    ]


# def test_read_series_csv(series_csv):
#     data = read_series_csv(series_csv)
#     print()
#     print(data)
