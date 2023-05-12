from django.urls import path

from . import views

app_name = "pick"

urlpatterns = [
    path("", views.index, name="index"),
]