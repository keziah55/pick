from .search import search
from .user_rating import set_user_rating


def index(request):
    if request.method == "GET":
        return _process_get(request)
    elif request.method == "POST":
        return _process_post(request)


def _process_get(request, *args, **kwargs):
    # see if the `request` object has a 'search' item
    try:
        search_str = request.GET["search"]
    # if not, use empty string
    except BaseException:
        search_str = ""
    return search(request, search_str, *args, **kwargs)


def _process_post(request, *args, **kwargs):
    return set_user_rating(request)
