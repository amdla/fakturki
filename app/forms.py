from django import forms
from decimal import Decimal
from app.models import Klient, Faktura, Pozycja


class KlientForm(forms.ModelForm):
    """
    Updated form for creating/updating a Klient, with manual NIP input.
    """

    class Meta:
        model = Klient
        fields = ['klient_nip']


class FakturaForm(forms.ModelForm):
    """
    Faktura form: Sprzedawca and Nabywca are now selected based on NIP input.
    """
    # Field for selecting if the invoice is 'kosztowa' or 'przychodowa'
    rodzaj_faktury = forms.ChoiceField(
        choices=[('kosztowa', 'Kosztowa'), ('przychodowa', 'Przychodowa')],
        label='Rodzaj Faktury',
    )

    klient_nip = forms.CharField(max_length=10, label="NIP klienta", required=True)

    class Meta:
        model = Faktura
        fields = [
            'faktura_numer',
            'klient_nip',
            'data_zakupu',
            'data_otrzymania_dokumentu',
            'rodzaj_faktury',  # Include the new field
        ]
        widgets = {
            'data_zakupu': forms.DateInput(attrs={'type': 'date'}),
            'data_otrzymania_dokumentu': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        rodzaj_faktury = cleaned_data.get('rodzaj_faktury')

        if rodzaj_faktury == 'kosztowa':
            cleaned_data['czy_kosztowa'] = True
        else:
            cleaned_data['czy_kosztowa'] = False

        return cleaned_data


class PozycjaForm(forms.ModelForm):
    faktura = forms.ModelChoiceField(
        queryset=Faktura.objects.order_by('faktura_numer'),
        label='Faktura'
    )

    class Meta:
        model = Pozycja
        fields = [
            'faktura',
            'opis_zdarzenia_gospodarczego',
            'netto',
            'brutto',
            'stawka',
        ]

    def clean(self):
        cleaned_data = super().clean()
        netto = cleaned_data.get('netto')
        brutto = cleaned_data.get('brutto')
        stawka = cleaned_data.get('stawka')

        # If both None => error, if both are set => check consistency
        if netto and brutto and stawka:
            # Quick consistency check
            rate = Decimal('0') if stawka in ['ZW', 'NP'] else Decimal(stawka) / Decimal('100')
            expected_brutto = (netto * (Decimal('1') + rate)).quantize(Decimal('0.01'))
            if (expected_brutto - brutto).copy_abs() > Decimal('0.01'):
                self.add_error('brutto', "Wprowadzone netto i brutto nie pasują do stawki VAT. ")
        elif (not netto) and (not brutto):
            # If both are empty, that’s invalid
            raise forms.ValidationError("Musisz wypełnić przynajmniej netto lub brutto.")

        return cleaned_data
