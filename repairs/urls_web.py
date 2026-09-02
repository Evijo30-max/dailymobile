from django.urls import path
from .views_web import DemandeReparationWebView

urlpatterns = [
    path('reparation/', DemandeReparationWebView.as_view(), name='web-demande-reparation'),
]