from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.utils import timezone

import barcode
from barcode.writer import ImageWriter
import random
from io import BytesIO

from .models import Author, BookCopy, BorrowRecord, Book
from .forms import (
    BorrowAndReturnForm, BookForm, AuthorForm, BookCopyFormSet,
                    NoFieldBorrowReturnForm
)



class IndexTemplateView(generic.ListView):
    model = Book
    template_name = "myApp/index.html"
    context_object_name = 'all_books'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     borrowed_records = BorrowRecord.objects.filter(returned_at__isnull=True)
    #     borrowed_books = Book.objects.filter(borrowed_books__in=borrowed_records)
    #     available_books = Book.objects.exclude(
    #         id__in=borrowed_books.values_list('id', flat=True)
    #     )
    #     context['borrowed_books'] = borrowed_books
    #     context['available_books'] = available_books
    #     return context


@staff_member_required
@login_required
def book_transactions(request):
    result = None
    form = BorrowAndReturnForm(request.POST or None)
    if form.is_valid():
        cd = form.cleaned_data
        barcode=cd['code']
        select=cd['select']

        book = BookCopy.objects.filter(barcode=barcode).first()
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
    return render(request, 'myApp/transactions.html',
                  {'form': form, 'result': result})


@login_required
def return_summary(request, pk):
    record = get_object_or_404(BorrowRecord, pk=pk)
    fee_data = record.get_total_debt_till_now()
    return render(request, 'myApp/return_summary.html',
                  {'record': record, 'fee_data': fee_data})



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
    success_url = reverse_lazy('myApp:add_copy_book')

    def test_func(self):
        return self.request.user.is_staff


class BookCopyCreateView(UserPassesTestMixin, LoginRequiredMixin, generic.View):
    template_name = "myApp/add_book_copy.html"
    success_url = reverse_lazy('myApp:home')

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        formset = BookCopyFormSet(queryset=BookCopy.objects.none())
        return render(request, self.template_name, {"formset": formset})

    def post(self, request, *args, **kwargs):
        formset = BookCopyFormSet(request.POST, request.FILES)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data:
                    book_copy = form.save(commit=False)
                    if not book_copy.barcode:
                        book_copy.barcode = generate_unique_barcode()
                        if not book_copy.barcode_image:
                            create_and_assign_barcode(book_copy)
                    book_copy.save()
            return redirect(self.success_url)
        return render(request, self.template_name, {"formset": formset})


class BookUpdateView(UserPassesTestMixin, LoginRequiredMixin, generic.UpdateView):
    model = Book
    form_class = BookForm
    template_name = "myApp/edit_book.html"
    success_url = reverse_lazy('myApp:home')

    def test_func(self):
        return self.request.user.is_staff


def create_and_assign_barcode(book):
    """
    Create barcode image and assign it to the book field.
    """
    barcode_str = book.barcode
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
    book.barcode_image.save(file_name, django_file, save=False)


def generate_unique_barcode(length=12):
    """
    If admin didn't add the barcode manually create a random one
    which is also unique and doesn't exist.
    """
    while True:
        code = ''.join(random.choices('0123456789', k=length))
        if not BookCopy.objects.filter(barcode=code).exists():
            return code


@staff_member_required
@login_required
def inventory_dashboard(request):
    main_books = Book.objects.select_related('author'
                                             ).prefetch_related('copies')
    copy_books = BookCopy.objects.select_related('book'
                                                 ).prefetch_related(
                                                     'borrow_records')
    return render(request,'myApp/inventory_dashboard.html',
        {
            'main_books': main_books,
            'copy_books': copy_books,
        }
    )


@staff_member_required
@login_required
def update_stock(request, pk):
    book = get_object_or_404(BookCopy, pk=pk)

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
                messages.success(request,
                                 f"Stock for '{book.title}' decreased.")
            else:
                messages.warning(request,
                                 f"Stock for '{book.title}' cannot go below zero.")
        else:
            messages.error(request, 'Invalid action.')
    return redirect('myApp:inventory-dashboard')


@login_required
def borrow_book(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if BorrowRecord.objects.filter(
        book_copy__book=book,
        borrower=request.user
        ).exists():
        messages.warning(
            request,
            'You have already borrowed a copy of this book.')
        return redirect('myApp:my_borrows_list')

    if request.method == "POST":
        form = NoFieldBorrowReturnForm(request.POST)
        if form.is_valid():
            book_copy = book.copies.filter(is_available=True).first()
            if book_copy is not None:
                form.instance.book_copy = book_copy
                form.instance.borrower = request.user
                form.save()
                book_copy.is_available = False
                book_copy.save()
                messages.success(
                    request,
                    f'You borrowed {book_copy.book.title} successfully.')
            else:
                messages.warning(
                    request,
                    'Unfortunately there is no any available copy of this book.')
            return redirect('myApp:home')

    form = NoFieldBorrowReturnForm()
    return render(request, 'myApp/borrow_book.html', {"form": form,
                                                      "book": book})

@login_required
def my_borrows_list(request):
    records = BorrowRecord.objects.filter(
        borrower=request.user
        ).select_related('book_copy', 'book_copy__book')

    total_debt = 0
    for record in records:
        record.total_fee = record.get_total_fee()
        total_debt += record.total_fee

    return render(request, 'myApp/my_borrows_list.html', {
        "records": records,
        "total_debt": total_debt,
    })



@login_required
def return_book(request, pk):
    record = get_object_or_404(BorrowRecord, pk=pk)
    if record.returned_at:
        messages.warning(request, 'You have already returned this book.')
        return redirect('myApp:my_borrows_list')

    if request.method == 'POST':
        form = NoFieldBorrowReturnForm(request.POST)
        if form.is_valid():
            record.returned_at = timezone.now()
            record.book_copy.is_available = True
            record.book_copy.save()
            record.save()
            return redirect('myApp:return_summary', pk=pk)
    form = NoFieldBorrowReturnForm()
    return render(request, 'myApp/return_book.html',
                  {
                      "book": record.book_copy.book,
                      "form": form,
                  })

