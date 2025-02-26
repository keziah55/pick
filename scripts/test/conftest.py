import pytest
from pathlib import Path

@pytest.fixture
def data_dir():

    return Path(__file__).parent.joinpath("data")

@pytest.fixture
def films_txt(data_dir):
    return data_dir.joinpath("films.txt")

@pytest.fixture
def patch_csv(data_dir):
    return data_dir.joinpath("minimal_db.csv")

@pytest.fixture
def physical_media_csv(data_dir):
    return data_dir.joinpath("physical_media_minimal.csv")

@pytest.fixture
def expected_patch_filenames():
    return [
        Path("Before_Midnight.mkv"),
        Path("Before_Sunrise.mkv"),
        Path("Before_Sunset.mkv"),
        Path("Juste Avant La Nuit.mkv"),
        Path("the nightmare before christmas"),
        Path("before the devil knows you're dead"),
        Path("Men_in_Black_2.mkv"),
        Path("Men_in_Black_3.mkv"),
        Path("Men_In_Black.mkv"),
        Path("Lord of the Rings The Fellowship of the Rings.mkv"),
        Path("Lord of the Rings The Two Towers.mkv"),
        Path("Lord of the Rings The Return of the King.mkv"),
        Path("Lord of the Rings The Fellowship of the Rings Extended.mkv"),
        Path("Lord of the Rings The Two Towers Extended.mkv"),
        Path("Lord of the Rings The Return of the King Extended.mkv"),
        Path("Skyfall.mkv"),
        Path("spectre"),
        Path("No_Time_to_Die.mkv"),
        Path("Koyaanisqatsi.mkv"),
        Path("Powaqqatsi.mkv"),
        Path("Die Hard.mkv"),
    ]

@pytest.fixture
def expected_films_filenames():
    return [Path("Drive.mkv")]