from typing import NamedTuple, Optional
from imdb.parser.http import IMDbHTTPAccessSystem as CinemagoerType  # used for type hint
from imdb.Person import Person as IMDbPerson


class PersonInfo(NamedTuple):
    id: str
    """IMDb ID for person."""
    name: str
    """Person's name."""
    alias: Optional[str] = None
    """Optional other name by which this person is known,"""


def _is_id_str(s: str) -> bool:
    """Return True if string `s` can be cast to int (and thus is an ID)"""
    try:
        int(s)
    except Exception:
        return False
    else:
        return True


def _name_to_id(name: str, cinemagoer: CinemagoerType) -> str:
    """
    Given `name` string, return IMDb ID string

    Note that, if `name` is an ID string, it will simply be returned.

    Raises
    ------
    RuntimeError
        If searching for the person's name returned no values.
    """
    if not _is_id_str(name):
        people = cinemagoer.search_person(name)
        if len(people) == 0:
            raise RuntimeError(f"Could not find IMDb ID for person '{name}'")
        name = people[0].getID()
    return name


def make_personinfo(person, cinemagoer: CinemagoerType) -> PersonInfo:
    """
    Create PersonInfo for given `person`.

    Note that `person` can be an imdb.Person.Person instance, an ID string
    or a name string.
    """
    if isinstance(person, IMDbPerson):
        id_str = person.getID()
        name = person["name"]
    elif _is_id_str(person):
        person = cinemagoer.get_person(person)
        id_str = person.getID()
        name = person["name"]
    else:
        id_str = _name_to_id(person)
        name = person
    return PersonInfo(id_str, name)
