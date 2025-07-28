from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_list, name='trading_list'),
    path('create/', views.create_trading_record, name='create_trading_record'),
    path('close/<int:record_id>/', views.close_position, name='close_position'),
    path('current-price/', views.get_current_price, name='get_current_price'),
    path('search/', views.search_records, name='search_records'),
] 