from django.urls import path
from . import views



app_name = 'myApp'

urlpatterns = [
    path('return-summary/<int:pk>/', views.return_summary, name='return_summary'),
    path('edit-book/<int:pk>/', views.BookUpdateView.as_view(), name='edit-book'),
    path('update-stock/<int:pk>/', views.update_stock, name='update-stock'),
    path('dashboard-management/', views.inventory_dashboard, name='inventory-dashboard'),
    path('transactions/', views.book_transactions, name='transactions'),
    path('add-copy-book/', views.BookCopyCreateView.as_view(), name='add_copy_book'),
    path('add-book/', views.BookCreateView.as_view(), name='add-book'),
    path('add-author/', views.AuthorCreateView.as_view(), name='add-author'),
    path('borrow-book/<int:pk>/', views.borrow_book, name='borrow_book'),
    path('my-borrows/', views.my_borrows_list, name='my_borrows_list'),
    path('return-book/<int:pk>/', views.return_book, name='return_book'),
    path('chart-data/', views.chart_data, name='chart_data'),
    path('generate-report-pdf/', views.generate_report_pdf, name='generate_report_pdf'),
    path('', views.IndexTemplateView.as_view(), name='home'),
]