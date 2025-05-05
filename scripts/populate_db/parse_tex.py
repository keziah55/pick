import re
from pathlib import Path
from typing import NamedTuple, Optional
from mediabrowser.models import VisionItem


class AltDescription(NamedTuple):
    title: str
    directors: list[str]
    year: int
    filename: str
    description: str


# def _parse_text_re(text, database="default") -> list[AltDescription]:
#     regex = re.compile(
#         r"\\film\{(?P<title>.+?)\}\{(?P<director>.+?)\}\{(?P<year>.+?)\}\{(?P<filename>.+?)\}\{(?P<description>.+?)\}",
#         re.DOTALL,
#     )

#     alt_descs: list[AltDescription] = []

#     for m in regex.finditer(text):
#         title, director, year, filename, desc = [s.strip() for s in m.groups()]

#         directors = _get_directors(director)
#         year, year_2 = _get_years(year)

#         alt_desc = AltDescription(
#             title=title,
#             directors=directors,
#             year=year,
#             year_2=year_2,
#             filename=filename,
#             description=desc,
#         )

#         print(alt_desc)


def _parse_text(text: str) -> list[AltDescription]:
    alt_descs: list[AltDescription] = []

    sub_str = None

    for line in text.split("\n"):
        if "\\film{" in line:
            if sub_str is not None:
                alt_descs += _parse_sub_str(sub_str)
            sub_str = line
        elif sub_str is not None:
            sub_str += f" {line}"

    if sub_str is not None:
        alt_descs += _parse_sub_str(sub_str)

    return alt_descs


def _parse_sub_str(sub_str):
    # print()
    sub_str = re.sub(r"\s+", " ", sub_str)
    # print(sub_str)

    m = re.match(
        r" ?\\film\{(?P<title>.+?)\}\{(?P<director>.+?)\}\{(?P<year>.+?)\}\{(?P<filename>.+?)\}",
        sub_str,
    )
    if m is None:
        raise ValueError(f"Could not get initial fields from '{sub_str}'")

    title, director, year, filename = [s.strip() for s in m.groups()]

    filenames = get_filenames(filename)
    years = _get_years(year)

    if len(filenames) == 0:
        raise RuntimeError(f"Error when trying to split filename '{filename}'")

    if len(filenames) != len(years):
        raise RuntimeError(f"Filenames and years do not match up: {filenames=}, {years=}")

    multi = len(filenames) > 1

    directors = _get_directors(director, multi)

    desc = sub_str[m.span()[1] :]
    desc = _get_desc(desc)

    # print(title)
    # print(directors)
    # print(years)
    # print(filenames)
    # print(desc)

    alt_descs = []
    for n, director in enumerate(directors):
        alt_descs.append(
            AltDescription(
                title=title,
                directors=director,
                year=years[n],
                filename=filenames[n],
                description=desc,
            )
        )
    return alt_descs


def get_filenames(filename_str: str) -> list[str]:
    return re.split(r"; ?", filename_str)


def _get_directors(director_str: str, multi=False) -> list[str]:
    """Directors may be 'and'ed for a single film. For multiple films, comma separated."""
    if multi:
        return re.split(r" and |, ?", director_str)
    else:
        return re.split(r" and ", director_str)


def _get_years(year_str: str) -> tuple[int, Optional[int]]:
    years = re.split(" ?, ?", year_str)
    return [int(year) for year in years]


    # if (m := re.match(r"(?P<year1>\d{4}),(?P<year2>\d{4})", year_str)) is not None:
    #     year, year_2 = [int(y) for y in m.groups()]
    # elif (m := re.match(r"\d{4}", year_str)) is not None:
    #     year = int(year_str)
    #     year_2 = None
    # else:
    #     raise ValueError(f"Could not parse year(s) from '{year_str}'")
    # return year, year_2


def _get_desc(desc_str: str) -> str:
    return _get_outer_paren(desc_str)


def _get_outer_paren(s, mode="{}") -> str:
    """Return text in outer parentheses."""
    open_p, close_p = mode
    count = None
    s = s.strip()
    text = ""
    for char in s:
        if char == open_p:
            if count is None:
                count = 0
            count += 1
        elif char == close_p:
            if count is None:
                raise RuntimeError(
                    f"Closing paren {close_p} found before opening paren {open_p} in string {s}"
                )
            count -= 1

        text += char

        if count == 0:
            break
        elif count < 0:
            raise RuntimeError(
                f"Negative paren count. String: '{s}'; current gathered text: {text}"
            )

    return text


def get_descriptions(filename: Path) -> list[AltDescription]:
    text = filename.read_text()
    text = text[:980]
    # text = text[-800:]
    return _parse_text(text)
