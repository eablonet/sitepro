from django.urls import path
from . import views

app_name = "cahier_edition"
urlpatterns = [
    path("", views.cahier_edition, name="edition"),
    path("semaine/<int:semaine_id>/ajouter/",
        views.entree_creer, name="entree_creer"),
    path("entree/<int:pk>/",
        views.entree_modifier, name="entree_modifier"),
]