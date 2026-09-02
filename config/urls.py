from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/catalogue/', include('catalogue.urls')),
    path('api/orders/', include('orders.urls')),
    path('', include('catalogue.urls_web')),
    path('', include('users.urls_web')),
    path('', include('orders.urls_web')),
    path('', include('repairs.urls_web')),
]