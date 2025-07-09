from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta



class Author(models.Model):
    name = models.CharField(max_length=264)

    def __str__(self):
        return f'{self.name} ({self.books.count()} books)'


class Book(models.Model):
    title = models.CharField(max_length=264)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    barcode = models.CharField(max_length=250, unique=True, blank=True, null=True)
    barcode_image = models.ImageField(upload_to='images/barcode/', blank=True, null=True)
    daily_rent = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], default=1)

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
    rented_days = models.PositiveIntegerField(default=3)
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-borrowed_at']
        unique_together = ('book', 'borrower', 'returned_at')

    def total_fee(self):
        base_fee = self.book.daily_rent * self.rented_days
        overdue_days = 0
        overdue_fee = 0
        if self.is_overdue():
            due_date = self.due_date()
            overdue_days = (timezone.now().date() - due_date.date()).days
            overdue_fee = overdue_days * self.book.daily_rent * 2
        total = base_fee + overdue_fee
        return {'base_fee':base_fee, 'overdue_days':overdue_days, 'overdue_fee':overdue_fee, 'total':total}

    def is_overdue(self):
        """Check if the book return is overdue."""
        return timezone.now() > self.due_date()

    def due_date(self):
        return self.borrowed_at + timedelta(days=self.rented_days)

    def return_book(self):
        """Mark the book as returned and increase stock."""
        if not self.returned_at:
            self.returned_at = timezone.now()
            self.book.return_copy()
            self.save()

    def __str__(self):
        status = "Returned" if self.returned_at else "Not Returned"
        return f"{self.borrower.username} - {self.book.title} ({status})"
