from django.urls import path

from app import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Klient
    path('klienci/', views.klient_list, name='klient_list'),
    path('klienci/create/', views.klient_create, name='klient_create'),
    path('klienci/update/<int:pk>/', views.klient_update, name='klient_update'),
    path('klienci/delete/<int:pk>/', views.klient_delete, name='klient_delete'),

    # Faktura
    path('faktury/', views.faktura_list, name='faktura_list'),
    path('faktury/create/', views.faktura_create, name='faktura_create'),
    path('faktury/update/<str:pk>/', views.faktura_update, name='faktura_update'),
    path('faktury/delete/<str:pk>/', views.faktura_delete, name='faktura_delete'),

    # PozycjaFaktury
    path('pozycje/', views.pozycja_list, name='pozycja_list'),
    path('pozycje/create/', views.pozycja_create, name='pozycja_create'),
    path('pozycje/update/<int:pk>/', views.pozycja_update, name='pozycja_update'),
    path('pozycje/delete/<int:pk>/', views.pozycja_delete, name='pozycja_delete'),

    # JPK_VAT URLs
    path('jpk-vat/select-period/', views.jpk_vat_select_period, name='jpk_vat_select_period'),
    path('jpk-vat/generate/', views.generate_jpk_vat, name='generate_jpk_vat'),
    path('jpk-vat/jpk_vat_preview/', views.jpk_vat_preview, name='download_jpk_vat'),

]
