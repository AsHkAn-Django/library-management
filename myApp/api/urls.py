from . import views
from django.urls import path


app_name = "myApp"

urlpatterns = [
    path('authors/', views.AuthorAPIView.as_view(), name='authors_api'),
]
