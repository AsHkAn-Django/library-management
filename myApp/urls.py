from django.urls import path
from . import views



app_name = 'myApp'

urlpatterns = [
    path('transactions/', views.book_transactions, name='transactions'),
    path('add_book/', views.BookCreateView.as_view(), name='add-book'),
    path('add_author/', views.AuthorCreateView.as_view(), name='add-author'),
    path('edit_book/<int:pk>/', views.BookUpdateView.as_view(), name='edit-book'),
    path('return-summary/<int:pk>/', views.return_summary, name='return-summary'),
    path('', views.IndexTemplateView.as_view(), name='home'),
]