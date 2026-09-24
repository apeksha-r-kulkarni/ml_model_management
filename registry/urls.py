from django.urls import path
from . import views

urlpatterns = [
    path('', views.ModelRegistrationPageView.as_view(), name='index'),
    path('api/models/register/', views.ModelRegistrationAPIView.as_view(), name='register_model'),
    path("api/models/", views.ModelsAPIView.as_view(), name="list_models"),
    path("api/architectures/", views.ArchitecturesAPIView.as_view(), name="architectures_api"),
    path('api/models/<str:mlflow_name>/version/<int:version>/', views.DeleteModelAPIView.as_view(), name='delete_model'),
]
