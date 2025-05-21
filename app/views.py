import datetime
from calendar import monthrange
from datetime import date

import requests
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse

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


def jpk_select_period(request):
    current_year = date.today().year

    # Create month choices
    months = [
        (f'month-{m}', f"{name} {current_year}")
        for m, name in [
            (1, 'Styczeń'), (2, 'Luty'), (3, 'Marzec'),
            (4, 'Kwiecień'), (5, 'Maj'), (6, 'Czerwiec'),
            (7, 'Lipiec'), (8, 'Sierpień'), (9, 'Wrzesień'),
            (10, 'Październik'), (11, 'Listopad'), (12, 'Grudzień')
        ]
    ]

    # Create quarter choices
    quarters = [
        (f'q{q}', f'{num} kwartał {current_year}')
        for q, num in [(1, 'I'), (2, 'II'), (3, 'III'), (4, 'IV')]
    ]

    periods = [('header', 'Pojedyncze miesiące')] + months + [('header', 'Kwartały')] + quarters

    if request.method == 'POST':
        selected = request.POST.get('period')

        if selected.startswith('month-'):
            # Handle monthly selection
            month = int(selected.split('-')[1])
            start_date = date(current_year, month, 1)
            last_day = monthrange(current_year, month)[1]
            end_date = date(current_year, month, last_day)
            period_type = 'month'

        elif selected.startswith('q'):
            # Handle quarterly selection
            quarter = int(selected[1])
            month_start = (quarter - 1) * 3 + 1
            start_date = date(current_year, month_start, 1)

            month_end = month_start + 2
            last_day = monthrange(current_year, month_end)[1]
            end_date = date(current_year, month_end, last_day)
            period_type = 'quarter'

        else:
            messages.error(request, "Nieprawidłowy wybór okresu")
            return redirect('jpk_select_period')

        return redirect(reverse('generate_jpk') + f'?start={start_date}&end={end_date}&type={period_type}')

    return render(request, 'jpk/select_period.html', {
        'periods': periods,
        'current_year': current_year
    })


def generate_jpk(request):
    # Get parameters from URL
    start_date = date.fromisoformat(request.GET.get('start'))
    end_date = date.fromisoformat(request.GET.get('end'))
    period_type = request.GET.get('type', 'month')

    # Get invoices
    faktury = Faktura.objects.filter(
        data_zakupu__gte=start_date,
        data_zakupu__lte=end_date
    ).prefetch_related('pozycja_set')

    # Get company data
    try:
        company = Klient.objects.get(klient_nip="8212527420")
    except Klient.DoesNotExist:
        return HttpResponse("Błąd konfiguracji: brak danych firmy", status=500)

    context = {
        'company': company,
        'faktury': faktury,
        'start_date': start_date,
        'end_date': end_date,
        'period_type': period_type,
        'generation_date': date.today(),
    }

    # Choose template based on period type
    template_name = 'jpk/jpk_quarterly.xml' if period_type == 'quarter' else 'jpk/jpk_monthly.xml'

    xml_content = render_to_string(template_name, context)

    response = HttpResponse(xml_content, content_type='application/xml')
    filename = f"JPK_{period_type}_{start_date}_{end_date}.xml"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
