from django.urls import path

from . import views

app_name = 'colloscope'

urlpatterns = [
    path('colles/colloscope/', views.colloscope, name='colloscope'),
    path('colles/colloscope/acces/', views.acces, name='acces'),
    path('colles/colloscope/deconnexion/', views.deconnexion, name='deconnexion'),
]