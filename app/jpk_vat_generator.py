from datetime import datetime, date
from decimal import Decimal

from django.http import HttpResponse
from django.template.loader import render_to_string

from app.models import Klient, Faktura


def generate_jpk_vat_xml(start_date, end_date, period_type='month'):
    """
    Główna funkcja generująca JPK_VAT XML

    Args:
        start_date (date): Data początkowa okresu
        end_date (date): Data końcowa okresu
        period_type (str): 'month' lub 'quarter'

    Returns:
        str: Gotowy XML JPK_VAT
    """

    # Pobierz dane naszej firmy
    try:
        company = Klient.objects.get(klient_nip="8212527420")
    except Klient.DoesNotExist:
        raise ValueError("Brak danych firmy w bazie (NIP: 8212527420)")

    # Pobierz faktury z wybranego okresu - używamy data_zakupu zamiast data_wystawienia
    faktury = Faktura.objects.filter(
        data_zakupu__gte=start_date,
        data_zakupu__lte=end_date
    ).prefetch_related('pozycja_set', 'sprzedawca', 'nabywca')

    # Przygotuj dane do JPK_VAT
    jpk_data = prepare_jpk_vat_data(company, faktury, start_date, end_date, period_type)

    # Wygeneruj XML
    template_name = 'XSD/jpk_vat.xml'
    xml_content = render_to_string(template_name, jpk_data)

    return xml_content


def prepare_jpk_vat_data(company, faktury, start_date, end_date, period_type):
    """
    Przygotowuje dane do generowania JPK_VAT XML
    """

    # Rozdziel faktury na sprzedaż i zakupy
    faktury_sprzedaz = []
    faktury_zakup = []

    for faktura in faktury:
        if faktura.czy_kosztowa:
            # Faktura kosztowa = zakup (my jesteśmy nabywcą)
            faktury_zakup.append(faktura)
        else:
            # Faktura przychodowa = sprzedaż (my jesteśmy sprzedawcą)
            faktury_sprzedaz.append(faktura)

    # Przygotuj wiersze sprzedaży
    sprzedaz_wiersze = []
    for i, faktura in enumerate(faktury_sprzedaz, 1):
        kontrahent = faktura.nabywca

        # Grupuj pozycje według stawek VAT
        pozycje_grouped = group_pozycje_by_vat(faktura.pozycja_set.all())

        wiersz = {
            'lp': i,
            'nip_nabywcy': kontrahent.klient_nip if kontrahent else '',
            'nazwa_nabywcy': kontrahent.klient_nazwa if kontrahent else '',
            'adres_nabywcy': kontrahent.klient_adres if kontrahent else '',
            'dowod_sprzedazy': faktura.faktura_numer,
            'data_wystawienia': faktura.data_zakupu,  # Używamy data_zakupu jako data wystawienia
            'data_sprzedazy': faktura.data_zakupu,  # Data sprzedaży = data zakupu
            'pozycje_vat': pozycje_grouped,
            'kwota_netto': faktura.netto,
            'kwota_vat': faktura.kwota_vat,
            'kwota_brutto': faktura.brutto
        }
        sprzedaz_wiersze.append(wiersz)

    # Przygotuj wiersze zakupów
    zakup_wiersze = []
    for i, faktura in enumerate(faktury_zakup, 1):
        kontrahent = faktura.sprzedawca

        # Grupuj pozycje według stawek VAT
        pozycje_grouped = group_pozycje_by_vat(faktura.pozycja_set.all())

        wiersz = {
            'lp': i,
            'nip_dostawcy': kontrahent.klient_nip if kontrahent else '',
            'nazwa_dostawcy': kontrahent.klient_nazwa if kontrahent else '',
            'adres_dostawcy': kontrahent.klient_adres if kontrahent else '',
            'dowod_zakupu': faktura.faktura_numer,
            'data_zakupu': faktura.data_zakupu,
            'data_otrzymania': faktura.data_otrzymania_dokumentu or faktura.data_zakupu,  # Fallback na data_zakupu
            'pozycje_vat': pozycje_grouped,
            'kwota_netto': faktura.netto,
            'kwota_vat': faktura.kwota_vat,
            'kwota_brutto': faktura.brutto
        }
        zakup_wiersze.append(wiersz)

    # Oblicz podsumowania VAT
    vat_summary = calculate_vat_summary(faktury_sprzedaz, faktury_zakup)

    # Przygotuj dane dla szablonu
    jpk_data = {
        'company': company,
        'start_date': start_date,
        'end_date': end_date,
        'period_type': period_type,
        'generation_date': datetime.now(),
        'sprzedaz_wiersze': sprzedaz_wiersze,
        'zakup_wiersze': zakup_wiersze,
        'vat_summary': vat_summary,
        'wariant_formularza': get_wariant_formularza(period_type)
    }

    return jpk_data


def group_pozycje_by_vat(pozycje):
    """
    Grupuje pozycje faktury według stawek VAT
    """
    grouped = {}

    for pozycja in pozycje:
        stawka = pozycja.stawka

        if stawka not in grouped:
            grouped[stawka] = {
                'netto': Decimal('0'),
                'vat': Decimal('0'),
                'brutto': Decimal('0')
            }

        grouped[stawka]['netto'] += pozycja.netto or Decimal('0')
        grouped[stawka]['vat'] += pozycja.kwota_vat or Decimal('0')
        grouped[stawka]['brutto'] += pozycja.brutto or Decimal('0')

    return grouped


def calculate_vat_summary(faktury_sprzedaz, faktury_zakup):
    """
    Oblicza podsumowanie VAT dla całego okresu
    """
    summary = {
        'sprzedaz': {
            '23': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '8': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '5': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '0': {'netto': Decimal('0'), 'vat': Decimal('0')},
            'ZW': {'netto': Decimal('0'), 'vat': Decimal('0')},
            'NP': {'netto': Decimal('0'), 'vat': Decimal('0')},
        },
        'zakup': {
            '23': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '8': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '5': {'netto': Decimal('0'), 'vat': Decimal('0')},
            '0': {'netto': Decimal('0'), 'vat': Decimal('0')},
            'ZW': {'netto': Decimal('0'), 'vat': Decimal('0')},
            'NP': {'netto': Decimal('0'), 'vat': Decimal('0')},
        }
    }

    # Podsumuj sprzedaż
    for faktura in faktury_sprzedaz:
        for pozycja in faktura.pozycja_set.all():
            stawka = str(pozycja.stawka)  # Konwertuj na string dla spójności
            if stawka in summary['sprzedaz']:
                summary['sprzedaz'][stawka]['netto'] += pozycja.netto or Decimal('0')
                summary['sprzedaz'][stawka]['vat'] += pozycja.kwota_vat or Decimal('0')

    # Podsumuj zakupy
    for faktura in faktury_zakup:
        for pozycja in faktura.pozycja_set.all():
            stawka = str(pozycja.stawka)  # Konwertuj na string dla spójności
            if stawka in summary['zakup']:
                summary['zakup'][stawka]['netto'] += pozycja.netto or Decimal('0')
                summary['zakup'][stawka]['vat'] += pozycja.kwota_vat or Decimal('0')

    # Oblicz VAT należny, naliczony i do zapłaty
    vat_nalezny = sum(summary['sprzedaz'][stawka]['vat'] for stawka in summary['sprzedaz'])
    vat_naliczony = sum(summary['zakup'][stawka]['vat'] for stawka in summary['zakup'])
    vat_do_zaplaty = vat_nalezny - vat_naliczony

    summary['vat_nalezny'] = vat_nalezny
    summary['vat_naliczony'] = vat_naliczony
    summary['vat_do_zaplaty'] = vat_do_zaplaty

    return summary


def get_wariant_formularza(period_type):
    """
    Określa wariant formularza JPK_VAT
    """
    if period_type == 'month':
        return '3'  # Miesięczny
    elif period_type == 'quarter':
        return '4'  # Kwartalny
    else:
        return '3'  # Domyślnie miesięczny


def generate_jpk_vat_response(start_date, end_date, period_type='month'):
    """
    Generuje odpowiedź HTTP z plikiem JPK_VAT XML
    """
    try:
        xml_content = generate_jpk_vat_xml(start_date, end_date, period_type)

        response = HttpResponse(xml_content, content_type='application/xml')
        filename = f"JPK_VAT_{period_type}_{start_date.strftime('%Y%m')}_{end_date.strftime('%Y%m')}.xml"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return HttpResponse(f"Błąd generowania JPK_VAT: {str(e)}", status=500)


# Funkcja pomocnicza do integracji z istniejącym widokiem
def generate_jpk_vat_view(request):
    """
    Widok Django do generowania JPK_VAT - zamiennik dla generate_jpk
    """
    # Pobierz parametry z URL
    start_date = date.fromisoformat(request.GET.get('start'))
    end_date = date.fromisoformat(request.GET.get('end'))
    period_type = request.GET.get('type', 'month')

    return generate_jpk_vat_response(start_date, end_date, period_type)


# Funkcja testowa
def test_jpk_vat_generation():
    """
    Funkcja testowa do sprawdzenia generowania JPK_VAT
    """
    from datetime import date

    # Testuj dla kwietnia 2025
    start_date = date(2025, 3, 1)
    end_date = date(2025, 4, 1)

    try:
        xml_content = generate_jpk_vat_xml(start_date, end_date, 'month')
        print("JPK_VAT wygenerowany pomyślnie!")
        print(f"Długość XML: {len(xml_content)} znaków")
        return xml_content
    except Exception as e:
        print(f"Błąd: {str(e)}")
        return None
