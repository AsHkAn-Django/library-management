from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from django.core.files.base import ContentFile

import barcode
from barcode.writer import ImageWriter
import random
from io import BytesIO


class Author(models.Model):
    name = models.CharField(max_length=264)

    def __str__(self):
        return f'{self.name} ({self.books.count()} books)'


class Book(models.Model):
    title = models.CharField(max_length=264)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='books'
    )
    image = models.ImageField(
        upload_to='images/books/',
        blank=True, null=True
    )
    daily_rent = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=1
    )

    @property
    def stock(self):
        """Number of available copies."""
        return self.copies.filter(is_available=True).count()

    def __str__(self):
        return f'{self.title} by {self.author.name} ({self.copies.count()} copies)'


class BookCopy(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='copies'
    )
    barcode = models.CharField(
        max_length=250,
        unique=True,
        blank=True,
        null=True
    )
    barcode_image = models.ImageField(
        upload_to='images/barcodes/',
        blank=True,
        null=True
    )
    is_available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = self.generate_unique_barcode()
            self.create_and_assign_barcode()
        elif not self.barcode_image:
            self.create_and_assign_barcode()

        super().save(*args, **kwargs)

    def create_and_assign_barcode(self):
        """
        Create barcode image and assign it to the book field.
        """
        barcode_str = self.barcode
        BarcodeClass = barcode.get_barcode_class('code128')
        ean = BarcodeClass(barcode_str, writer=ImageWriter())

        # Save barcode image to memory buffer
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)

        # Create Django-friendly file object
        file_name = f"{barcode_str}.png"
        django_file = ContentFile(buffer.read(), name=file_name)

        # Save to the ImageField using Django's storage backend (Cloudflare R2)
        self.barcode_image.save(file_name, django_file, save=False)


    def generate_unique_barcode(self, length=12):
        """
        If admin didn't add the barcode manually create a random one
        which is also unique and doesn't exist.
        """
        while True:
            code = ''.join(random.choices('0123456789', k=length))
            if not BookCopy.objects.filter(barcode=code).exists():
                return code

    def __str__(self):
        status = "Available" if self.is_available else "Borrowed"
        return f"Copy of {self.book.title} ({status})"


class BorrowRecord(models.Model):
    book_copy = models.ForeignKey(
        BookCopy,
        on_delete=models.CASCADE,
        related_name='borrow_records'
    )
    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='borrowed_books'
    )
    rented_days = models.PositiveIntegerField(default=3)
    borrowed_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    total_fee = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ['-borrowed_at']
        unique_together = ('book_copy', 'borrower', 'returned_at')

    def get_total_fee(self):
        data = self.get_total_debt_till_now()
        self.total_fee = data['total']
        self.save()
        return self.total_fee

    def get_total_debt_till_now(self):
        """Bring the debt of user till now."""
        base_fee = self.book_copy.book.daily_rent * self.rented_days

        overdue_days = 0
        overdue_fee = 0

        if self.is_overdue():
            due_date = self.due_date()
            overdue_days = (timezone.now().date() - due_date.date()).days
            overdue_fee = overdue_days * self.book_copy.book.daily_rent * 2

        total = base_fee + overdue_fee
        return {
            'base_fee': base_fee,
            'overdue_days': overdue_days,
            'overdue_fee': overdue_fee,
            'total': total,
        }

    def get_days_borrowed(self):
        """Bring the time the book has been with the user till now."""
        return (timezone.now().date() - self.borrowed_at.date()).days

    def is_overdue(self):
        """Check if the book return is overdue."""
        return timezone.now() > self.due_date()

    def due_date(self):
        return self.borrowed_at + timedelta(days=self.rented_days)

    def return_book(self):
        """Mark the book as returned and free the copy."""
        if not self.returned_at:
            self.returned_at = timezone.now()
            self.book_copy.is_available = True
            self.book_copy.save()
            self.save()

    def __str__(self):
        status = "Returned" if self.returned_at else "Not Returned"
        return f"{self.borrower.username} - {self.book_copy.book.title} ({status})"
