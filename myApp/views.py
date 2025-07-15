from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile

import barcode
from barcode.writer import ImageWriter
import os
import random
from io import BytesIO

from .models import Author, Book, BorrowRecord
from .forms import BorrowAndReturnForm, BookForm, AuthorForm



class IndexTemplateView(generic.ListView):
    model = Book
    template_name = "myApp/index.html"
    context_object_name = 'all_books'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # borrowed_books = Book.objects.filter(
        #     Exists(
        #         BorrowRecord.objects.filter(
        #             book=OuterRef('pk'),
        #             returned_at__isnull=True
        #         )
        #     )
        # )

        #----- WE CAN USE THE CODE ABOVE INSTEAD OF THIS ONE WHICH IS MORE DJANGO LIKE------
        borrowed_records = BorrowRecord.objects.filter(returned_at__isnull=True)
        borrowed_books = Book.objects.filter(borrowed_books__in=borrowed_records)
        #---------------------------------------------------------------------------------------------

        # Books that are NOT currently borrowed (either never borrowed or returned)
        available_books = Book.objects.exclude(
            id__in=borrowed_books.values_list('id', flat=True)
        )

        context['borrowed_books'] = borrowed_books
        context['available_books'] = available_books
        return context


@staff_member_required
@login_required
def book_transactions(request):
    result = None
    form = BorrowAndReturnForm(request.POST or None)
    if form.is_valid():
        cd = form.cleaned_data
        barcode=cd['code']
        select=cd['select']

        book = Book.objects.filter(barcode=barcode).first()
        if not book:
            messages.warning(request, "There is no book with the code you entered.")
            return redirect('myApp:transactions')

        record = BorrowRecord.objects.filter(book=book).order_by('-borrowed_at').first()

        if select == 'Borrow':
            if not cd['user']:
                messages.warning(request, "Please select a user to borrow the book.")
                return redirect('myApp:transactions')
            if not record or record.returned_at:
                if book.borrow():
                    if cd['rented_days']:
                        BorrowRecord.objects.create(book=book, borrower=cd['user'], rented_days=cd['rented_days'])
                    else:
                        BorrowRecord.objects.create(book=book, borrower=cd['user'])
                    messages.success(request, f"The user ({cd['user']}) borrowed the book ({book.title}) successfully.")
                else:
                    messages.warning(request, "This book is out of stock.")
            else:
                messages.warning(request, f"User ({cd['user']}) has already borrowed the book ({book.title}) and should return it.")

        elif select == 'Return':
            if record and not record.returned_at:
                record.return_book()
                messages.success(request, f"The book ({book.title}) has been returned successfully.")
                return redirect('myApp:return-summary', pk=record.pk)
            else:
                messages.warning(request, f"This book ({book.title}) is not borrowed to be returned.")

        elif select == 'Track':
            if record and not record.returned_at:
                messages.info(request, f"The user ({record.borrower.username}) has the book ({book.title}).")
            else:
                messages.info(request, f"The book ({book.title}) is in the library.")

        return redirect('myApp:transactions')
    return render(request, 'myApp/transactions.html', {'form': form, 'result': result})


@staff_member_required
@login_required
def return_summary(request, pk):
    record = get_object_or_404(BorrowRecord, pk=pk)
    fee_data = record.total_fee()
    return render(request, 'myApp/return_summary.html', {'record': record, 'fee_data': fee_data})



class AuthorCreateView(UserPassesTestMixin, LoginRequiredMixin, generic.CreateView):
    model = Author
    form_class = AuthorForm
    template_name = "myApp/add_author.html"
    success_url = reverse_lazy('myApp:add-book')

    def test_func(self):
        return self.request.user.is_staff


class BookCreateView(UserPassesTestMixin, LoginRequiredMixin, generic.CreateView):
    model = Book
    form_class = BookForm
    template_name = "myApp/add_book.html"
    success_url = reverse_lazy('myApp:home')

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        if not form.instance.barcode:
            form.instance.barcode = generate_unique_barcode()
        create_and_assign_barcode(form)
        return super().form_valid(form)


class BookUpdateView(UserPassesTestMixin, LoginRequiredMixin, generic.UpdateView):
    model = Book
    form_class = BookForm
    template_name = "myApp/edit_book.html"
    success_url = reverse_lazy('myApp:home')

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        if not form.instance.barcode:
            form.instance.barcode = generate_unique_barcode()
        if not form.instance.barcode_image:
            create_and_assign_barcode(form)
        return super().form_valid(form)


def create_and_assign_barcode(form):
    """
    Create barcode image and assign it to the book field.
    """
    barcode_str = form.instance.barcode
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
    form.instance.barcode_image.save(file_name, django_file, save=False)


def generate_unique_barcode(length=12):
    """
    If admin didn't add the barcode manually create a random one
    which is also unique and doesn't exist.
    """
    while True:
        code = ''.join(random.choices('0123456789', k=length))
        if not Book.objects.filter(barcode=code).exists():
            return code


@staff_member_required
@login_required
def inventory_dashboard(request):
    books = Book.objects.all()
    return render(request, 'myApp/inventory_dashboard.html', {'books': books})


@staff_member_required
@login_required
def update_stock(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'increase':
            book.stock += 1
            book.save()
            messages.success(request, f"Stock for '{book.title}' increased.")
        elif action == 'decrease':
            if book.stock > 0:
                book.stock -= 1
                book.save()
                messages.success(request, f"Stock for '{book.title}' decreased.")
            else:
                messages.warning(request, f"Stock for '{book.title}' cannot go below zero.")
        else:
            messages.error(request, 'Invalid action.')

    return redirect('myApp:inventory-dashboard')