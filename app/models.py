from decimal import Decimal
from django.db import models


class Klient(models.Model):
    klient_id = models.AutoField(primary_key=True)
    klient_nazwa = models.CharField(max_length=255)
    klient_nip = models.CharField(max_length=10, unique=True)
    status_vat = models.CharField(max_length=50, default="Czynny")
    klient_regon = models.CharField(max_length=14, blank=True, null=True)
    klient_krs = models.CharField(max_length=10, blank=True, null=True)
    klient_adres = models.CharField(max_length=255, blank=True, null=True)
    data_rejestracji = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.klient_nazwa


class Faktura(models.Model):
    faktura_id = models.AutoField(primary_key=True)
    faktura_numer = models.CharField(max_length=255, unique=True)
    sprzedawca = models.ForeignKey(Klient, on_delete=models.CASCADE, related_name='sprzedawca')
    nabywca = models.ForeignKey(Klient, on_delete=models.CASCADE, related_name='nabywca')

    data_zakupu = models.DateField()
    data_otrzymania_dokumentu = models.DateField()

    netto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    brutto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    kwota_vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # New field to define whether the invoice is 'kosztowa' or 'przychodowa'
    czy_kosztowa = models.BooleanField(default=False)

    def __str__(self):
        return self.faktura_numer

    def update_sums(self):
        """
        Sums up netto, brutto, and kwota_vat from all Pozycja objects
        belonging to this Faktura.
        """
        pozycje = self.pozycja_set.all()

        sum_netto = Decimal('0')
        sum_brutto = Decimal('0')
        sum_kwota_vat = Decimal('0')

        for p in pozycje:
            # Each p.netto or p.brutto might be None, but usually not after the form+save.
            # So we handle None safely by converting to decimal 0 if needed.
            sum_netto += p.netto or Decimal('0')
            sum_brutto += p.brutto or Decimal('0')
            sum_kwota_vat += p.kwota_vat or Decimal('0')

        self.netto = sum_netto
        self.brutto = sum_brutto
        self.kwota_vat = sum_kwota_vat

        # Update all three fields in the DB in one shot
        self.save(update_fields=['netto', 'brutto', 'kwota_vat'])


class Pozycja(models.Model):
    VAT_CHOICES = [
        ('23', '23%'),
        ('8', '8%'),
        ('5', '5%'),
        ('0', '0%'),
        ('ZW', 'ZW'),  # treat as 0%
        ('NP', 'NP'),  # treat as 0%
    ]

    faktura = models.ForeignKey(Faktura, on_delete=models.CASCADE)

    # Optional
    opis_zdarzenia_gospodarczego = models.CharField(max_length=255, blank=True, null=True)

    # ALLOW NETTO/BRUTTO to be truly empty at DB level
    netto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    brutto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    stawka = models.CharField(max_length=3, choices=VAT_CHOICES, default='23')  # TODO: fix kurwa bo jest dwa razy

    kwota_vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        """
        If only netto is set, compute brutto. If only brutto is set, compute netto.
        Then kwota_vat = brutto - netto. Finally, update the parent Faktura sums.
        """
        if self.stawka in ['ZW', 'NP']:
            vat_rate = Decimal('0')
        else:
            vat_rate = Decimal(self.stawka) / Decimal('100')

        # Convert None to Decimal('0') for safety, but let's see if we can handle both None.
        _netto = self.netto or Decimal('0')
        _brutto = self.brutto or Decimal('0')

        if not self.netto and self.brutto:
            # Derive netto from brutto
            factor = (Decimal('1') + vat_rate)
            _netto = (self.brutto / factor).quantize(Decimal('0.01'))

        elif self.netto and not self.brutto:
            # Derive brutto from netto
            _brutto = (self.netto * (Decimal('1') + vat_rate)).quantize(Decimal('0.01'))

        # If both self.netto and self.brutto are None, that indicates
        # the form let something slip by, but let's handle gracefully:
        # We'll keep them as zeroes in that scenario, or you could raise an error here.

        # Now set them back to the model fields
        self.netto = _netto
        self.brutto = _brutto
        self.kwota_vat = (self.brutto - self.netto).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

        self.faktura.update_sums()

    def delete(self, *args, **kwargs):
        faktura_ref = self.faktura
        super().delete(*args, **kwargs)
        faktura_ref.update_sums()

    def __str__(self):
        return self.opis_zdarzenia_gospodarczego or "Brak opisu"
