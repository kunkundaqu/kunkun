from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField, BooleanField, ExpressionWrapper
from .models import TradingRecord
from .utils import get_crypto_price, get_stock_price, get_forex_price, get_commodity_price
import json
from decimal import Decimal
from datetime import datetime

def trading_list(request):
    records = TradingRecord.objects.all().annotate(
        is_open=ExpressionWrapper(Q(status='open'), output_field=BooleanField())
    ).order_by('-is_open', '-entry_time')
    paginator = Paginator(records, 10)
    page = request.GET.get('page')
    records = paginator.get_page(page)
    return render(request, 'trading/list.html', {'records': records})

@require_http_methods(["POST"])
def create_trading_record(request):
    try:
        data = json.loads(request.body)
        record = TradingRecord(
            asset_type=data['asset_type'],
            symbol=data['symbol'],
            direction=data['direction'],
            quantity=Decimal(str(data['quantity'])),
            entry_price=Decimal(str(data['entry_price'])),
            entry_time=datetime.fromisoformat(data['entry_time'].replace('Z', '+00:00')),
            notes=data.get('notes', '')
        )
        record.save()
        return JsonResponse({'status': 'success', 'id': record.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["POST"])
def close_position(request, record_id):
    try:
        data = json.loads(request.body)
        record = get_object_or_404(TradingRecord, id=record_id)
        
        if record.status == 'closed':
            return JsonResponse({'status': 'error', 'message': '该仓位已经平仓'}, status=400)
        
        record.exit_price = Decimal(str(data['exit_price']))
        record.exit_time = datetime.fromisoformat(data['exit_time'].replace('Z', '+00:00'))
        record.status = 'closed'
        record.notes = data.get('notes', record.notes)
        record.calculate_profit_loss()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["GET"])
def get_current_price(request):
    try:
        asset_type = request.GET.get('asset_type')
        symbol = request.GET.get('symbol')
        
        if asset_type == 'crypto':
            price = get_crypto_price(symbol)
        elif asset_type == 'stock':
            price = get_stock_price(symbol)
        elif asset_type == 'forex':
            price = get_forex_price(symbol)
        elif asset_type == 'commodity':
            price = get_commodity_price(symbol)
        else:
            return JsonResponse({'status': 'error', 'message': '不支持的资产类型'}, status=400)
        
        return JsonResponse({'status': 'success', 'price': str(price)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["GET"])
def search_records(request):
    query = request.GET.get('query', '')
    records = TradingRecord.objects.filter(
        Q(symbol__icontains=query) |
        Q(notes__icontains=query)
    ).order_by('-entry_time')
    
    paginator = Paginator(records, 10)
    page = request.GET.get('page')
    records = paginator.get_page(page)
    
    return render(request, 'trading/list.html', {'records': records, 'query': query}) 