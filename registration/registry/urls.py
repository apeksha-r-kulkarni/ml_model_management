from django.urls import path
from . import views

urlpatterns = [
    path('', views.register_page, name='index'),
    path('api/models/register/', views.register_model, name='register_model'),
    path("api/models/", views.list_models, name="list_models"),
    path("api/models/find/", views.find_model, name="find_model"),
    path("api/models/update/", views.update_model, name="update_model"),
    path("api/models/purposes/", views.list_purposes, name="list_purposes"),
    path('api/models/<str:mlflow_name>/version/<int:version>/', views.delete_model, name='delete_model'),
]
