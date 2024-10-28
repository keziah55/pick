from django.contrib import admin

from .models import VisionItem, Person, Genre, Keyword

for mdl in [VisionItem, Person, Genre, Keyword]:
    admin.site.register(mdl)