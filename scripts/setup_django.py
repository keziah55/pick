from pathlib import Path
import sys
import os


def setup_django():
    """Set paths, import django and call `django.setup()`."""
    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pick.settings")
    import django

    django.setup()
