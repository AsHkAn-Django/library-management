from django.urls import path
from . import views



app_name = 'myApp'

urlpatterns = [
    path('return-summary/<int:pk>/', views.return_summary, name='return-summary'),
    path('edit-book/<int:pk>/', views.BookUpdateView.as_view(), name='edit-book'),
    path('update-stock/<int:pk>/', views.update_stock, name='update-stock'),
    path('dashboard-management/', views.inventory_dashboard, name='inventory-dashboard'),
    path('transactions/', views.book_transactions, name='transactions'),
    path('add-copy-book/', views.BookCopyCreateView.as_view(), name='add_copy_book'),
    path('add-book/', views.BookCreateView.as_view(), name='add-book'),
    path('add-author/', views.AuthorCreateView.as_view(), name='add-author'),
    path('', views.IndexTemplateView.as_view(), name='home'),
]