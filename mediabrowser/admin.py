from django.contrib import admin

from .models import VisionItem, MediaSeries, Person, Genre, Keyword

for mdl in [VisionItem, MediaSeries, Person, Genre, Keyword]:
    admin.site.register(mdl)