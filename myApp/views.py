from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Author, Book
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
        if cd['select'] == 'Borrow':
            result = 'you chose borrow'
        elif cd['select'] == 'Return':
            result = 'you chose return'
        elif cd['select'] == 'Track':
            result = 'you chose track'

    return render(request, 'myApp/transactions.html', {'form': form, 'result': result})


