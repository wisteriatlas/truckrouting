from django.urls import path

from . import views

urlpatterns = [
    path("geocode", views.GeocodeView.as_view()),
    path("analyze", views.AnalyzeView.as_view()),
    path("health", views.HealthView.as_view()),
]
