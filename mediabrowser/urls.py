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
    path("person/<int:person>", views.view_person, name="view_person"),
    path("visionitem/<int:pk>", views.view_visionitem, name="view_visionitem"),
    path("rating/<int:rating>", views.view_user_rating, name="view_user_rating"),
]

# Serving the media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += staticfiles_urlpatterns()
