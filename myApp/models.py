from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone



class Author(models.Model):
    name = models.CharField(max_length=264)

    def __str__(self):
        return f'{self.name} ({self.books.count()} books)'


class Book(models.Model):
    title = models.CharField(max_length=264)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    barcode = models.CharField(max_length=250, unique=True)

    @property
    def is_available(self):
        return self.stock > 0

    def borrow(self):
        """Decrease stock when book is borrowed."""
        if self.stock > 0:
            self.stock -= 1
            self.save()
            return True
        return False

    def return_copy(self):
        """Increase stock when book is returned."""
        self.stock += 1
        self.save()

    def __str__(self):
        return f'{self.title} by {self.author.name} (Stock: {self.stock})'


class BorrowRecord(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowed_books')
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_books')
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-borrowed_at']
        unique_together = ('book', 'borrower', 'returned_at')  # optional constraint

    def return_book(self):
        """Mark the book as returned and increase stock."""
        if not self.returned_at:
            self.returned_at = timezone.now()
            self.book.return_copy()
            self.save()

    def __str__(self):
        status = "Returned" if self.returned_at else "Not Returned"
        return f"{self.borrower.username} - {self.book.title} ({status})"
