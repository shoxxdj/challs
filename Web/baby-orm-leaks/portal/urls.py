from django.urls import path
from . import views

urlpatterns = [
    path('',          views.login_page, name='login'),
    path('api/login', views.api_login,  name='api_login'),
    path('api/docs',  views.api_docs,   name='api_docs'),
]
