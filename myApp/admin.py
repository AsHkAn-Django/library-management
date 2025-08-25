from django.contrib import admin
from .models import Author, Book, BorrowRecord, BookCopy


admin.site.register(Author)
admin.site.register(Book)
admin.site.register(BorrowRecord)
admin.site.register(BookCopy)