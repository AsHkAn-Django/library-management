from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from .models import Author, Book
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin



class BookContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = self.kwargs.get('pk')
        context['book'] = get_object_or_404(Book, pk=book_id)
        return context



class IndexView(LoginRequiredMixin, generic.ListView):
    model = Book
    context_object_name = 'books'
    template_name = "myApp/index.html"



class BorrowBookView(LoginRequiredMixin, BookContextMixin, generic.FormView):
    success_url = reverse_lazy('myApp:home')
    template_name = "myApp/borrow_book.html"

    def form_valid(self, form):
        book, borrows, returns = get_book_borrows_returns(self.kwargs.get('pk'), self.request.user)
        if borrows.exists() and borrows.count() > returns.count():
            messages.warning(self.request, "You've already borrowed this book. You can't do it again!")
            return redirect('myApp:home')
        if book.decrease_stock():
            update_and_save_form(form, self.request.user, book)
            messages.success(self.request, 'You borrowed a book successfully.')
        else:
            messages.warning(self.request, 'Sorry, there is not enough book in the library!')
        return super().form_valid(form)



class ReturnBookView(LoginRequiredMixin, BookContextMixin, generic.FormView):
    success_url = reverse_lazy('myApp:home')
    template_name = "myApp/return_book.html"

    def form_valid(self, form):
        book, borrows, returns = get_book_borrows_returns(self.kwargs.get('pk'), self.request.user)
        if borrows.count() == returns.count():
            messages.warning(self.request, "You've already returned this book!")
            return redirect('myApp:home')
        book.increase_stock()
        update_and_save_form(form, self.request.user, book, False)
        messages.success(self.request, 'You returned a book successfully.')
        return super().form_valid(form)







def update_and_save_form(form, user, book, borrow=True):
    if borrow:
        form.instance.borrower = user
    else:
        form.instance.returner = user
    form.instance.book = book
    form.save()




