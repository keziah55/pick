from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views
# from .views import VisionItemList

app_name = "pick"

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:search_str>/", views.search, name="search"),
    path("person/<int:person>", views.get_person, name="get_person")
]

# Serving the media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += staticfiles_urlpatterns()