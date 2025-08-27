from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import JsonResponse



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
        user=cd['user']

        book = BookCopy.objects.filter(barcode=barcode).first()
        if not book:
            messages.warning(request, "There is no book with the code you entered.")
            return redirect('myApp:transactions')

        record = BorrowRecord.objects.filter(book_copy=book).order_by('-borrowed_at').first()

        if select == 'Borrow':
            if not user:
                messages.warning(request, "Please select a user to borrow the book.")
                return redirect('myApp:transactions')
            if not record or record.returned_at:
                if book.is_available:
                    if cd['rented_days']:
                        BorrowRecord.objects.create(
                            book_copy=book, borrower=user, rented_days=cd['rented_days'])
                    else:
                        BorrowRecord.objects.create(
                            book_copy=book, borrower=user)
                    book.is_available = False
                    book.save()
                    messages.success(
                        request,
                        f"The user ({user}) borrowed the book ({book.book.title}) successfully.")
                else:
                    messages.warning(request, "This book is out of stock.")
            else:
                messages.warning(
                    request,
                    f"User ({record.borrower.username}) borrowed the book ({book.book.title}) and should return it.")

        elif select == 'Return':
            if record and not record.returned_at:
                if record.borrower == user:
                    book.is_available = True
                    book.save()
                    record.returned_at = timezone.now()
                    record.save()
                    messages.success(
                                request,
                                f"The book ({book.book.title}) has been returned successfully.")
                    return redirect('myApp:return_summary', pk=record.pk)
                else:
                    messages.warning(
                        request,
                        f"This book ({book.book.title}) is borrowerd by another user.")
            else:
                messages.warning(request, f"This book ({book.book.title}) is not borrowed.")

        elif select == 'Track':
            if record and not record.returned_at:
                messages.info(
                    request,
                    f"The user ({record.borrower.username}) has the book ({book.book.title}).")
            else:
                messages.info(request, f"The book ({book.book.title}) is in the library.")

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
        borrower=request.user,
        returned_at__isnull=True
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


def chart_data(request):
    # each book how many copies has
    books = Book.objects.all()
    copies = [book.copies.count() for book in books]

    # each author how many books has

    # each author how many copies has

    # each book how many times were borrwed

    # the books wich are borrowed now

    # hot books

    # price of each book

    # the books with the highest revenue

    # data = {
    #     "labels": [
    #         "Red", "Blue", "Yellow", "Green", "Purple",
    #         "Orange", "Black", "White", "Gray", "Pink"
    #     ],
    #     "values": [12, 19, 3, 5, 2, 8, 15, 7, 10, 4],
    # }
    return JsonResponse(
        {
            "labels": [book.title for book in books],
            "values": copies
        }
    )