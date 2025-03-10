from ..populate_db.read_data_files import read_patch_csv, read_films_file
from ..populate_db.media_info import MediaInfoProcessor
from ..populate_db.progress_bar import ProgressBar

from pathlib import Path
from pprint import pprint

import pytest

DATABASE = "default"


@pytest.mark.skip("manual testing")
def test_filter_films():
    print()

    media_proc = MediaInfoProcessor()

    data_path = Path(__file__).parents[3].joinpath("pick-data")
    films_txt = data_path.joinpath("films.txt")
    patch_csv = data_path.joinpath("patch.csv")

    assert films_txt.exists()
    assert patch_csv.exists()

    films = read_films_file(films_txt)
    patch = read_patch_csv(patch_csv)

    films = [film for film in films if film in patch]

    progress = ProgressBar(len(films))

    results = {"best": [], "first": [], "neither": [], "both": []}

    # films = [Path("Apocalypse Now Final Cut.mp4")]
    for n, film in enumerate(films):
        title = film.stem
        title, year = media_proc._parse_title(title)
        possible_movies = media_proc._search_imdb_by_title(title, year)
        best_match = media_proc._get_best_match(title, possible_movies)

        target_imdb_id = patch[film]["media_id"]

        best_match_id = int(best_match.getID())
        first_match_id = int(possible_movies[0].getID())

        if best_match_id == first_match_id == target_imdb_id:
            results["both"].append(film)
        elif best_match_id == target_imdb_id:
            results["best"].append(film)
        elif first_match_id == target_imdb_id:
            results["first"].append(film)
        else:
            results["neither"].append(film)

        progress.progress(n + 1)

        # print(f"{film}: {target_imdb_id=}, {best_match_id=}, {first_match_id=}")
        # # pprint(possible_movies)
        # for m in possible_movies:
        #     print(m.data)

    # print(results)

    for key, file_names in results.items():
        print(f"{key}: {len(file_names)}")

        with open(f"{key}.txt", "w") as fileobj:
            text = "\n".join([str(f) for f in file_names])
            fileobj.write(text)
