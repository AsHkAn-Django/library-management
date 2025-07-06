from django.urls import path
from . import views

app_name = 'myApp'
urlpatterns = [
    path('return_book/<int:pk>', views.ReturnBookView.as_view(), name='return_book'),
    path('borrow_book/<int:pk>', views.BorrowBookView.as_view(), name='borrow_book'),
    path('', views.IndexView.as_view(), name='home'),
]