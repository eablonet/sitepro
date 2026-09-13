from django.urls import path
from . import views

app_name = "cahier_texte"
urlpatterns = [
    path("", views.cahier_texte, name="cahier"),
    path("cahier_texte/edition/", views.cahier_edition, name="edition"),
    path("cahier_texte/edition/semaine/<int:semaine_id>/ajouter/",
        views.entree_creer, name="entree_creer"),
    path("cahier_texte/edition/entree/<int:pk>/",
        views.entree_modifier, name="entree_modifier"),
]