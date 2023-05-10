from django.contrib import admin

from .models import MediaItem, MediaSeries, Person, Genre, Keyword

for mdl in [MediaItem, MediaSeries, Person, Genre, Keyword]:
    admin.site.register(mdl)