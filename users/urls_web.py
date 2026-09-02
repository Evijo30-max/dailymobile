from django.urls import path
from .views_web import LoginWebView, LogoutWebView, RegisterWebView

urlpatterns = [
    path('connexion/', LoginWebView.as_view(), name='web-login'),
    path('inscription/', RegisterWebView.as_view(), name='web-register'),
    path('deconnexion/', LogoutWebView.as_view(), name='web-logout'),
]