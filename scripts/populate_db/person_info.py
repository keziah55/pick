from typing import NamedTuple, Optional, Union
import imdbinfo
from imdbinfo.models import CastMember, PersonDetail, Person as IMDbPerson


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


def _name_to_id(name: str) -> str:
    """
    Given `name` string, return IMDb ID string

    Note that, if `name` is an ID string, it will simply be returned.

    Raises
    ------
    RuntimeError
        If searching for the person's name returned no values.
    """

    if not _is_id_str(name):
        people = imdbinfo.search_title(name).names
        if len(people) == 0:
            raise RuntimeError(f"Could not find IMDb ID for person '{name}'")
        name = people[0].id
    return name


def make_personinfo(
    person: Union[str, IMDbPerson, CastMember, PersonDetail], aliases: dict[str:str]
) -> PersonInfo:
    """
    Create PersonInfo for given `person`.

    Note that `person` can be any imdbinfo Person class, an ID string
    or a name string.
    """
    if isinstance(person, (IMDbPerson, CastMember, PersonDetail)):
        id_str = person.id
        name = person.name
    elif _is_id_str(person):
        person = imdbinfo.get_name(person)
        id_str = person.id
        name = person.name
    else:
        id_str = _name_to_id(person)
        name = person

    if (alias := aliases.get(int(id_str), None)) is not None:
        alias = alias["alias"]

    return PersonInfo(id_str, name, alias)
