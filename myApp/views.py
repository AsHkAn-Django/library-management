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
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.http import HttpResponse
import weasyprint


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
    # quries
    queried_authors = Author.objects.prefetch_related(
        'books',
        'books__copies',
        'books__copies__borrow_records'
    )

    queried_main_books = Book.objects.select_related(
        'author'
        ).prefetch_related(
        'copies'
    )

    # each book how many copies has
    books_list = [book.title for book in queried_main_books]
    copies = [book.copies.count() for book in queried_main_books]

    # each author how many copies has
    authors_list = [author.name for author in queried_authors]
    author_copies_count = [
        sum(book.copies.count() for book in author.books.all())
        for author in queried_authors
    ]

    # each author how many books has
    authors_list = authors_list
    author_books_count = [author.books.count() for author in queried_authors]

    # daily_rent of each book
    books_list = books_list
    daily_rent_list = [book.daily_rent for book in queried_main_books]

    # each book how many times were borrwed
    books_list = books_list
    book_borrowed_counts = [
        sum(len(copy.borrow_records.all()) for copy in book.copies.all())
        for book in queried_main_books
    ]

    # the books wich are borrowed now
    books_list = books_list
    books_are_borrowed_now = [
        sum(1 for copy in book.copies.all() if not copy.is_available)
        for book in queried_main_books
    ]

    # the books with the highest revenue
    books_list = books_list
    books_with_revenue = queried_main_books.annotate(
        revenue=Sum("copies__borrow_records__total_fee")
    )
    books_revenue = [book.revenue or 0 for book in books_with_revenue]

    # users base on the revenue
    users_with_revenue = get_user_model().objects.annotate(
        revenue=Sum("borrowed_books__total_fee")
    ).order_by('-revenue')
    users_list = [user.username for user in users_with_revenue]
    revenues_list = [user.revenue for user in users_with_revenue]

    return JsonResponse(
        {
            "chart1": {
                "labels": books_list,
                "values": copies
            },
            "chart2": {
                "labels": authors_list,
                "values": author_copies_count
            },
            "chart3": {
                "labels": authors_list,
                "values": author_books_count
            },
            "chart4": {
                "labels": books_list,
                "values": daily_rent_list
            },
            "chart5": {
                "labels": books_list,
                "values": book_borrowed_counts
            },
            "chart6": {
                "labels": books_list,
                "values": books_are_borrowed_now
            },
            "chart7": {
                "labels": books_list,
                "values": books_revenue
            },
            "chart8": {
                "labels": users_list,
                "values": revenues_list
            }
        }
    )


@staff_member_required
@login_required
def generate_report_pdf(request):
    if request.method == 'POST':
        context = {
            "main_books": Book.objects.all(),
            "chart1_image": request.POST.get("chart1_image"),
            "chart2_image": request.POST.get("chart2_image"),
            "chart3_image": request.POST.get("chart3_image"),
            "chart4_image": request.POST.get("chart4_image"),
            "chart5_image": request.POST.get("chart5_image"),
            "chart6_image": request.POST.get("chart6_image"),
            "chart7_image": request.POST.get("chart7_image"),
            "chart8_image": request.POST.get("chart8_image"),
        }

        html_string = render_to_string("myApp/books_report_pdf.html", context, request=request)
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename="books_report.pdf'
        weasyprint.HTML(string=html_string).write_pdf(response)
        return response
