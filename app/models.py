from django.db import models


class Klient(models.Model):
    klient_id = models.AutoField(primary_key=True)
    klient_nazwa = models.CharField(max_length=255)  # name
    klient_nip = models.CharField(max_length=10, unique=True)  # nip
    status_vat = models.CharField(max_length=50, default="Czynny")  # statusVat
    klient_regon = models.CharField(max_length=14, blank=True, null=True)  # regon
    klient_krs = models.CharField(max_length=10, blank=True, null=True)  # krs
    klient_adres = models.CharField(max_length=255, blank=True, null=True)  # workingAddress
    data_rejestracji = models.DateField(blank=True, null=True)  # registrationLegalDate
    konta_bankowe = models.JSONField(default=list)  # accountNumbers

    def __str__(self):
        return self.klient_nazwa


class Faktura(models.Model):
    faktura_id = models.AutoField(primary_key=True)
    faktura_numer = models.CharField(max_length=255, unique=True)
    sprzedawca = models.ForeignKey(Klient, on_delete=models.CASCADE, related_name='sprzedawca')
    nabywca = models.ForeignKey(Klient, on_delete=models.CASCADE, related_name='nabywca')
    data_wyst = models.DateField()
    netto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    brutto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.faktura_numer


class Pozycja(models.Model):
    faktura = models.ForeignKey(Faktura, on_delete=models.CASCADE)
    towar_opis = models.CharField(max_length=255)
    pkwiu = models.CharField(max_length=255)
    cena_jednostkowa = models.DecimalField(max_digits=10, decimal_places=2)
    jednostka = models.CharField(max_length=255)
    ilosc = models.IntegerField()
    netto = models.DecimalField(max_digits=10, decimal_places=2)
    stawka = models.IntegerField()
    kwota_vat = models.DecimalField(max_digits=10, decimal_places=2)
    brutto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.towar_opis
