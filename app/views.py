import datetime

import requests
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect

from app.forms import KlientForm, FakturaForm, PozycjaForm
from app.models import Klient, Faktura, Pozycja


def home(request):
    return render(request, 'home.html')


########################################
# KLIENT CRUD
########################################

def klient_list(request):
    klienci = Klient.objects.all()
    return render(request, 'klient/klient_list.html', {'klienci': klienci})


def klient_create(request):
    if request.method == 'POST':
        form = KlientForm(request.POST)
        if form.is_valid():
            nip = form.cleaned_data['klient_nip']
            try:
                klient_data = fetch_klient_data_by_nip(nip)
                klient = Klient(**klient_data)
                klient.save()
                messages.success(request, f"Pomyślnie utworzono klienta o NIP {nip}.")
                return redirect('klient_list')
            except ValueError as e:
                form.add_error('klient_nip', str(e))
    else:
        form = KlientForm()
    return render(request, 'klient/klient_form.html', {'form': form})


def klient_update(request, pk):
    klient = get_object_or_404(Klient, pk=pk)
    if request.method == 'POST':
        form = KlientForm(request.POST, instance=klient)
        if form.is_valid():
            form.save()
            return redirect('klient_list')
    else:
        form = KlientForm(instance=klient)
    return render(request, 'klient/klient_form.html', {'form': form})


def klient_delete(request, pk):
    klient = get_object_or_404(Klient, pk=pk)
    if request.method == 'POST':
        klient.delete()
        return redirect('klient_list')
    return render(request, 'klient/klient_confirm_delete.html', {'klient': klient})


########################################
# FAKTURA CRUD
########################################

def faktura_list(request):
    faktury = Faktura.objects.all()
    return render(request, 'faktura/faktura_list.html', {'faktury': faktury})


def faktura_create(request):
    if request.method == 'POST':
        # Initialize the form with POST data upfront
        form = FakturaForm(request.POST)
        nip = request.POST.get('klient_nip', None)

        if nip:
            try:
                klient = Klient.objects.filter(klient_nip=nip).first()

                if klient:
                    # Ensure that we set the correct nabywca or sprzedawca
                    if request.POST.get('confirm_klient') == 'yes':
                        if form.is_valid():
                            faktura = form.save(commit=False)
                            faktura.nabywca = klient  # Assign the client to nabywca field
                            faktura.save()
                            messages.success(request, "Pomyślnie utworzono fakturę.")
                            return redirect('faktura_list')
                    else:
                        # Re-initialize form with initial NIP for confirmation
                        form = FakturaForm(initial={'klient_nip': nip})
                        return render(request, 'faktura/faktura_confirm_klient.html', {'klient': klient, 'form': form})
                else:
                    # Fetch and save new client from API
                    klient_data = fetch_klient_data_by_nip(nip)
                    klient = Klient(**klient_data)
                    klient.save()

                    # Proceed with form validation
                    if form.is_valid():
                        faktura = form.save(commit=False)
                        faktura.nabywca = klient  # Ensure that the client is assigned to nabywca
                        faktura.save()
                        messages.success(request, "Pomyślnie utworzono fakturę.")
                        return redirect('faktura_list')
            except ValueError as e:
                messages.error(request, f"Błąd: {str(e)}")
                return render(request, 'faktura/faktura_form.html', {'form': form})

        # Handle case where NIP is missing or form is invalid
        if form.is_valid():
            form.save()
            messages.success(request, "Pomyślnie utworzono fakturę.")
            return redirect('faktura_list')
        else:
            return render(request, 'faktura/faktura_form.html', {'form': form})
    else:
        form = FakturaForm()

    return render(request, 'faktura/faktura_form.html', {'form': form})


def faktura_update(request, pk):
    faktura = get_object_or_404(Faktura, pk=pk)
    if request.method == 'POST':
        form = FakturaForm(request.POST, instance=faktura)
        if form.is_valid():
            form.save()
            return redirect('faktura_list')
    else:
        form = FakturaForm(instance=faktura)
    return render(request, 'faktura/faktura_form.html', {'form': form})


def faktura_delete(request, pk):
    faktura = get_object_or_404(Faktura, pk=pk)
    if request.method == 'POST':
        faktura.delete()
        return redirect('faktura_list')
    return render(request, 'faktura/faktura_confirm_delete.html', {'faktura': faktura})


########################################
# POZYCJA FAKTURY CRUD
########################################

def pozycja_list(request):
    pozycje = Pozycja.objects.all()
    return render(request, 'pozycja/pozycja_list.html', {'pozycje': pozycje})


def pozycja_create(request):
    if request.method == 'POST':
        form = PozycjaForm(request.POST)
        if form.is_valid():
            form.save()  # Pozycja's save() auto-calculates missing fields
            return redirect('pozycja_list')
    else:
        form = PozycjaForm()
    return render(request, 'pozycja/pozycja_form.html', {'form': form})


def pozycja_update(request, pk):
    pozycja = get_object_or_404(Pozycja, pk=pk)
    if request.method == 'POST':
        form = PozycjaForm(request.POST, instance=pozycja)
        if form.is_valid():
            form.save()
            return redirect('pozycja_list')
    else:
        form = PozycjaForm(instance=pozycja)
    return render(request, 'pozycja/pozycja_form.html', {'form': form})


def pozycja_delete(request, pk):
    pozycja = get_object_or_404(Pozycja, pk=pk)
    if request.method == 'POST':
        pozycja.delete()
        return redirect('pozycja_list')
    return render(request, 'pozycja/pozycja_confirm_delete.html', {'pozycja': pozycja})


########################################
# EXTERNAL DATA FETCH
########################################

def fetch_klient_data_by_nip(nip: str) -> dict:
    """
    Example function to fetch data from WL API given a NIP
    and today's date. Returns a dict to populate the Klient model.
    Raises ValueError if invalid or no data.
    """
    BASE_URL = "https://wl-api.mf.gov.pl/api"
    date_str = datetime.date.today().strftime("%Y-%m-%d")

    if len(nip) != 10 or not nip.isdigit():
        raise ValueError("Niepoprawny format NIP (musi mieć 10 cyfr).")

    url = f"{BASE_URL}/search/nip/{nip}?date={date_str}"
    response = requests.get(url)

    if response.status_code != 200:
        data = response.json()
        error_msg = data.get("error", {}).get("message", "Błąd zewnętrznego API.")
        raise ValueError(f"API error: {error_msg}")

    data = response.json()
    subject = data.get("result", {}).get("subject")
    if not subject:
        raise ValueError("Brak danych dla podanego NIP.")

    return {
        "klient_nazwa": subject.get("name"),
        "klient_nip": subject.get("nip"),
        "status_vat": subject.get("statusVat", ""),
        "klient_regon": subject.get("regon"),
        "klient_krs": subject.get("krs"),
        "klient_adres": subject.get("workingAddress"),
        "data_rejestracji": subject.get("registrationLegalDate"),
    }
