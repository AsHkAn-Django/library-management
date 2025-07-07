from django.urls import path
from . import views



app_name = 'myApp'

urlpatterns = [
    path('transactions/', views.book_transactions, name='transactions'),
    path('', views.IndexView.as_view(), name='home'),
]