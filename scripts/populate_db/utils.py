from typing import Union

def imdb_id_to_str(imdb_id: Union[int, str]) -> str:
    """Return zero-padded string from `imdb_id`."""
    return f"{int(imdb_id):07d}"