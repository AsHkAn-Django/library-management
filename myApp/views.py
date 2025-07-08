from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Author, Book, BorrowRecord
from .forms import BorrowAndReturnForm



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

        record = BorrowRecord.objects.filter(book=book, borrower=request.user).first()

        if select == 'Borrow':
            if not record or record.returned_at:
                if book.borrow():
                    BorrowRecord.objects.create(book=book, borrower=request.user)
                    messages.success(request, f'You borrowed the book ({book.title}) successfully.')
                else:
                    messages.warning(request, "This book is out of stock.")
            else:
                messages.warning(request, f'You have already borrowed the book ({book.title}) and you should return it.')

        elif select == 'Return':
            if record and not record.returned_at:
                record.return_book()
                messages.success(request, f'You returned the book ({book.title}) successfully.')
            else:
                messages.warning(request, f'Your name is not in the system as a borrower for this book ({book.title}).')

        elif select == 'Track':
            if record and not record.returned_at:
                messages.info(request, f'The user ({record.borrower.username}) has the book ({book.title}).')
            else:
                messages.info(request, f'The book ({book.title}) is in the library.')

        return redirect('myApp:transactions')

    return render(request, 'myApp/transactions.html', {'form': form, 'result': result})




