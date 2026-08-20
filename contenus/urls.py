from django.urls import path
from . import views

app_name = 'contenus'

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('tp/', views.liste_tp, name='liste_tp'),
    path('devoirs/', views.liste_devoirs, name='liste_devoirs'),
    path('cours/', views.liste_cours, name='liste_cours'),
    path('fiches-outils/', views.liste_fiches_outils, name='liste_fiches_outils'),
    path('archives/', views.archives, name='archives'),
    path('archives/<str:annee_nom>/', views.archives, name='archives'),
]