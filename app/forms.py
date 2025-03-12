from django import forms

from app.models import Klient, Faktura, Pozycja


class KlientForm(forms.ModelForm):
    class Meta:
        model = Klient
        fields = ['klient_nip']


class FakturaForm(forms.ModelForm):
    class Meta:
        model = Faktura
        fields = ['faktura_numer', 'sprzedawca', 'nabywca', 'data_wyst']
        widgets = {
            'data_wyst': forms.DateInput(attrs={'type': 'date'})
        }


class PozycjaForm(forms.ModelForm):
    class Meta:
        model = Pozycja
        fields = '__all__'
