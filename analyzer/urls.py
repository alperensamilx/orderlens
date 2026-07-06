from django.contrib.auth.views import LogoutView
from django.urls import path

from . import api_views, views

app_name = 'analyzer'

urlpatterns = [
    path('', views.dataset_list, name='dataset_list'),
    path('map/<int:pk>/', views.map_columns, name='map_columns'),
    path('analyze/<int:pk>/', views.analyze_dataset, name='analyze'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.OrderLensLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/datasets/<int:pk>/stats/', api_views.DatasetStatsAPIView.as_view(), name='api_dataset_stats'),
]
