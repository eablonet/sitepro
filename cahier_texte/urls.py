from django.urls import path
from . import views

app_name = "cahier_texte"
urlpatterns = [path("cahier/cahier", views.cahier_texte, name="cahier")]