from django.urls import path
from . import views

urlpatterns = [
    path('', views.ModelRegistrationPageView.as_view(), name='index'),
    path('api/models/register/', views.ModelRegistrationAPIView.as_view(), name='register_model'),
    path("api/models/", views.ModelsAPIView.as_view(), name="list_models"),
    path("api/models/find/", views.FindModelAPIView.as_view(), name="find_model"),
    path("api/models/update/", views.UpdateModelAPIView.as_view(), name="update_model"),
    path("api/models/set-deployed/", views.SetDeployedVersionAPIView.as_view(), name="set_deployed_version"),
    path("api/models/purposes/", views.PurposesAPIView.as_view(), name="list_purposes"),
    path("api/models/architectures/", views.ArchitecturesAPIView.as_view(), name="list_architectures"),
    path("api/models/languages/", views.LanguagesAPIView.as_view(), name="list_languages"),
    path("api/models/environments/", views.EnvironmentsAPIView.as_view(), name="list_environments"),
    path('api/models/<str:mlflow_name>/version/<int:version>/', views.DeleteModelAPIView.as_view(), name='delete_model'),
]
