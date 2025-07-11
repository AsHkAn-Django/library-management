from django import forms
from django.contrib.auth import get_user_model

from .models import Book, Author


SELECT_CHOICES = [
    ('Borrow', 'Borrow'),
    ('Return', 'Return'),
    ('Track', 'Track')
]

class BorrowAndReturnForm(forms.Form):
    """A form for borrowing, returning, or tracking a book by barcode."""
    code = forms.CharField(
        max_length=250,
        label='Barcode',
        widget=forms.TextInput(attrs={'placeholder': 'Scan or enter barcode'})
    )
    select = forms.ChoiceField(choices=SELECT_CHOICES, label='Action')
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="Borrower (only for borrow)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    rented_days = forms.IntegerField(min_value=1, required=False, label='Days (only for borrow)',
                                     widget=forms.TextInput(attrs={'placeholder': 'Ex. 1'}))


class BookForm(forms.ModelForm):

    class Meta:
        model = Book
        fields = ['title', 'author', 'stock', 'barcode']


class AuthorForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = ['name']

