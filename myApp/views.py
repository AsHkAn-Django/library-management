from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

import barcode
from barcode.writer import ImageWriter
import os

from .models import Author, Book, BorrowRecord
from .forms import BorrowAndReturnForm, BookForm, AuthorForm



class IndexView(LoginRequiredMixin, generic.ListView):
    model = Book
    context_object_name = 'books'
    template_name = "myApp/index.html"


def book_transactions(request):
    result = None
    form = BorrowAndReturnForm(request.POST or None)
    if form.is_valid():
        cd = form.cleaned_data
        barcode=cd['code']
        select=cd['select']

        book = Book.objects.filter(barcode=barcode).first()
        if not book:
            messages.warning(request, 'There is no book with the code you entered.')
            return redirect('myApp:transactions')

        record = BorrowRecord.objects.filter(book=book).first()

        if select == 'Borrow':
            if not cd['user']:
                messages.warning(request, 'Please select a user to borrow the book.')
                return redirect('myApp:transactions')
            if not record or record.returned_at:
                if book.borrow():
                    BorrowRecord.objects.create(book=book, borrower=cd['user'])
                    messages.success(request, f'The user ({cd['user']}) borrowed the book ({book.title}) successfully.')
                else:
                    messages.warning(request, "This book is out of stock.")
            else:
                messages.warning(request, f'User ({cd['user']}) has already borrowed the book ({book.title}) and should return it.')

        elif select == 'Return':
            if record and not record.returned_at:
                record.return_book()
                messages.success(request, f'The book ({book.title}) has been returned successfully.')
            else:
                messages.warning(request, f'This book ({book.title}) is not borrowed to be returned.')

        elif select == 'Track':
            if record and not record.returned_at:
                messages.info(request, f'The user ({record.borrower.username}) has the book ({book.title}).')
            else:
                messages.info(request, f'The book ({book.title}) is in the library.')

        return redirect('myApp:transactions')
    return render(request, 'myApp/transactions.html', {'form': form, 'result': result})


class AuthorCreateView(generic.CreateView):
    model = Author
    form_class = AuthorForm
    template_name = "myApp/add_author.html"
    success_url = reverse_lazy('myApp:add-book')


class BookCreateView(generic.CreateView):
    model = Book
    form_class = BookForm
    template_name = "myApp/add_book.html"
    success_url = reverse_lazy('myApp:home')

    def form_valid(self, form):
        create_and_assign_barcode(form)
        return super().form_valid(form)


class BookUpdateView(generic.UpdateView):
    model = Book
    form_class = BookForm
    template_name = "myApp/edit_book.html"
    success_url = reverse_lazy('myApp:home')

    def form_valid(self, form):
        if not form.instance.barcode_image:
            create_and_assign_barcode(form)
        return super().form_valid(form)


def create_and_assign_barcode(form):
    barcode_str = form.cleaned_data['barcode']

    # Generate barcode image
    BarcodeClass = barcode.get_barcode_class('code128')
    ean = BarcodeClass(barcode_str, writer=ImageWriter())

    # Save to media path
    file_name = f"{barcode_str}.png"
    file_path = os.path.join(settings.MEDIA_ROOT, 'images', 'barcode', file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    ean.save(file_path[:-4]) # remove ".png" - save() adds it

    # Save image path to model field
    form.instance.barcode_image = f"images/barcode/{file_name}"