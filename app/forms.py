from django import forms
from decimal import Decimal
from app.models import Klient, Faktura, Pozycja


class KlientForm(forms.ModelForm):
    """
    Example form for creating/updating a Klient, only controlling klient_nip
    (since other fields might be fetched from an external API).
    """

    class Meta:
        model = Klient
        fields = ['klient_nip']


class FakturaForm(forms.ModelForm):
    """
    Factura form: sprzedawca/nabywca sorted by klient_nazwa,
    and date fields for data_zakupu, data_otrzymania_dokumentu.
    """
    sprzedawca = forms.ModelChoiceField(
        queryset=Klient.objects.order_by('klient_nazwa'),
        label='Sprzedawca'
    )
    nabywca = forms.ModelChoiceField(
        queryset=Klient.objects.order_by('klient_nazwa'),
        label='Nabywca'
    )

    class Meta:
        model = Faktura
        fields = [
            'faktura_numer',
            'sprzedawca',
            'nabywca',
            'data_zakupu',
            'data_otrzymania_dokumentu',
        ]
        widgets = {
            'data_zakupu': forms.DateInput(attrs={'type': 'date'}),
            'data_otrzymania_dokumentu': forms.DateInput(attrs={'type': 'date'}),
        }


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
                self.add_error('brutto', "Wprowadzone netto i brutto nie pasują do stawki VAT. ") #TODO: mozna 0 wpisac
        elif (not netto) and (not brutto):
            # If both are empty, that’s invalid
            raise forms.ValidationError("Musisz wypełnić przynajmniej netto lub brutto.")

        return cleaned_data
