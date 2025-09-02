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
def alias_csv(data_dir):
    return data_dir.joinpath("aliases.csv")


@pytest.fixture
def series_csv(data_dir):
    return data_dir.joinpath("minimal_media_series.csv")


@pytest.fixture
def description_csv(data_dir):
    return data_dir.joinpath("alt_descriptions.csv")


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
    return [
        Path("Drive.mkv"),
        Path("The Great Dictator.mkv"),
        Path("Alice in Wonderland (1999).mkv"),
    ]

@pytest.fixture
def expected_alt_descriptions():
    return [
        Path("Drive.mkv"),
        Path("spectre"),
        Path("before the devil knows you're dead"),
        Path("Lord of the Rings The Fellowship of the Rings.mkv"),
    ]


@pytest.fixture
def expected_imdb_ids():
    return {
        "Before_Midnight.mkv": 2209418,
        "Before_Sunrise.mkv": 112471,
        "Before_Sunset.mkv": 381681,
        "Juste Avant La Nuit.mkv": 73221,
        "the nightmare before christmas": 107688,
        "before the devil knows you're dead": 292963,
        "Men_in_Black_2.mkv": 120912,
        "Men_in_Black_3.mkv": 1409024,
        "Men_In_Black.mkv": 119654,
        "Lord of the Rings The Fellowship of the Rings.mkv": 120737,
        "Lord of the Rings The Two Towers.mkv": 167261,
        "Lord of the Rings The Return of the King.mkv": 167260,
        "Lord of the Rings The Fellowship of the Rings Extended.mkv": 120737,
        "Lord of the Rings The Two Towers Extended.mkv": 167261,
        "Lord of the Rings The Return of the King Extended.mkv": 167260,
        "Skyfall.mkv": 1074638,
        "spectre": 2379713,
        "No_Time_to_Die.mkv": 2382320,
        "Koyaanisqatsi.mkv": 85809,
        "Powaqqatsi.mkv": 95895,
        "Die Hard.mkv": 95016,
        "Drive.mkv": 780504,
        "The Great Dictator.mkv": 32553,
        "Alice in Wonderland (1999).mkv": 164993,
    }
