from django import forms

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
    select = forms.ChoiceField(
        choices=SELECT_CHOICES,
        label='Action'
    )