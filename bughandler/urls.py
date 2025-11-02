from django.urls import path
from .views import error_page
urlpatterns = [
    path('error_page/',error_page,name='error-page')
]
