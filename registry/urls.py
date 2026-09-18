from django.urls import path
from . import views

urlpatterns = [
    path('', views.register_page, name='index'),
    path('api/models/register/', views.register_model, name='register_model'),
    path("api/models/", views.list_models, name="list_models"),
    path("api/architectures/", views.architectures_api, name="architectures_api"),
    path('api/models/<str:mlflow_name>/version/<int:version>/', views.delete_model, name='delete_model'),
]
