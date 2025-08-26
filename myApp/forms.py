from django import forms
from django.forms import modelformset_factory, BaseFormSet, ValidationError
from django.contrib.auth import get_user_model

from .models import Book, Author, BookCopy, BorrowRecord


SELECT_CHOICES = [
    ('Borrow', 'Borrow'),
    ('Return', 'Return'),
    ('Track', 'Track')
]


class BorrowForm(forms.ModelForm):

    class Meta:
        model = BorrowRecord
        fields = []


class BorrowAndReturnForm(forms.Form):
    """A form for borrowing, returning, or tracking a book by barcode."""
    code = forms.CharField(
        max_length=250,
        label='Barcode',
        widget=forms.TextInput(
            attrs={'placeholder': 'Scan or enter barcode'}
        )
    )
    select = forms.ChoiceField(choices=SELECT_CHOICES, label='Action')
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="Borrower (only for borrow)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    rented_days = forms.IntegerField(
        min_value=1,
        required=False,
        label='Days (only for borrow)',
        widget=forms.TextInput(
            attrs={'placeholder': 'Ex. 1'}
        )
    )


class BookForm(forms.ModelForm):

    class Meta:
        model = Book
        fields = ['title', 'author', 'image', 'daily_rent']

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if Book.objects.filter(title__iexact=title).exists():
            raise forms.ValidationError('We already have this book.')
        return title

    def clean_daily_rent(self):
        daily_rent = self.cleaned_data.get('daily_rent')
        if daily_rent > 99:
            return forms.ValidationError('Be fair! It should be less than 100!')
        return daily_rent


class BookCopyForm(forms.ModelForm):
    class Meta:
        model = BookCopy
        fields = ['book', 'barcode', 'barcode_image']


BookCopyFormSet = modelformset_factory(
    BookCopy,
    form=BookCopyForm,
    extra=3,
    can_delete=True
)


class AuthorForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = ['name']

