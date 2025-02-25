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