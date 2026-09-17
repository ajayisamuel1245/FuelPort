#!/usr/bin/env python
"""
setup_api.py

Run this script once to create all API files for your Django project.
It will:
- Create an 'api' app directory with __init__.py, views.py, serializers.py, urls.py
- Populate them with fully functional API endpoints as described.

After running, you need to:
1. Install django-cors-headers: pip install django-cors-headers
2. Add 'corsheaders' to INSTALLED_APPS and MIDDLEWARE in settings.py
3. Set CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS for your React frontend.
4. Include the api URLs in your main urls.py: path('api/', include('api.urls'))
5. Ensure your existing views.py remains unchanged.

Run this script from your Django project root (where manage.py is).
"""

import os
import sys

def create_file(path, content):
    """Create a file with the given content, creating directories if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")

def main():
    # Base directory for the api app
    api_dir = 'api'

    # ========== api/__init__.py ==========
    init_content = ""
    create_file(os.path.join(api_dir, '__init__.py'), init_content)

    # ========== api/serializers.py ==========
    serializers_content = """from decimal import Decimal
from django.utils import timezone

def serialize_user(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }

def serialize_fuel_price(price):
    if not price:
        return None
    return {
        'price_per_litre': str(price.price_per_litre),
        'effective_from': price.effective_from.isoformat(),
        'set_by': price.set_by.username if price.set_by else None,
    }

def serialize_wallet(wallet):
    return {
        'balance': str(wallet.balance),
        'available_litres': str(wallet.available_litres),
    }

def serialize_purchase(purchase):
    return {
        'id': purchase.id,
        'litres_bought': str(purchase.litres_bought),
        'price_per_litre': str(purchase.price_per_litre),
        'total_amount': str(purchase.total_amount),
        'payment_reference': purchase.payment_reference,
        'created_at': purchase.created_at.isoformat(),
    }

def serialize_litre_lot(lot):
    if not lot:
        return None
    return {
        'id': lot.id,
        'litres_purchased': str(lot.litres_purchased),
        'litres_remaining': str(lot.litres_remaining),
        'price_per_litre': str(lot.price_per_litre),
        'expires_at': lot.expires_at.isoformat(),
        'status': lot.status,
        'days_left': max((lot.expires_at - timezone.now()).days, 0),
        'percent_remaining': int((lot.litres_remaining / lot.litres_purchased) * 100) if lot.litres_purchased else 0,
    }

def serialize_redemption(redemption):
    return {
        'id': redemption.id,
        'litres_redeemed': str(redemption.litres_redeemed),
        'qr_code': str(redemption.qr_code),
        'qr_expires_at': redemption.qr_expires_at.isoformat(),
        'status': redemption.status,
        'created_at': redemption.created_at.isoformat(),
        'redeemed_at': redemption.redeemed_at.isoformat() if redemption.redeemed_at else None,
        'station': redemption.station.name,
        'station_code': redemption.station.code,
        'verification_code': redemption.verificaton_code,
        'is_expired': redemption.is_expired,
    }

def serialize_station(station):
    return {
        'id': station.id,
        'name': station.name,
        'address': station.address,
        'code': station.code,
        'is_active': station.is_active,
        'created_at': station.created_at.isoformat(),
    }
"""
    create_file(os.path.join(api_dir, 'serializers.py'), serializers_content)

    # ========== api/views.py ==========
    views_content = """import json
import uuid
import traceback
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from io import BytesIO
import base64
import qrcode

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator

from ..models import (
    FuelPrice, Station, LitrePurchase, LitreLot,
    LitreWallet, InitializePaymentRecord, fuelRedemption
)
from ..utils_pay import initializePaystackPayment, verifyPayment
from .serializers import (
    serialize_user, serialize_fuel_price, serialize_wallet,
    serialize_purchase, serialize_litre_lot, serialize_redemption,
    serialize_station
)


# ---------- AUTH ----------
@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    first_name = data.get('firstname', '')
    last_name = data.get('lastname', '')
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')

    if not email or not password1 or not password2:
        return JsonResponse({'error': 'All details must be provided'}, status=400)
    if len(password1) < 6:
        return JsonResponse({'error': 'Password is too short'}, status=400)
    if password1 != password2:
        return JsonResponse({'error': 'Passwords do not match'}, status=400)
    if username and User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)

    try:
        user = User.objects.create_user(
            username=username, email=email, password=password1,
            first_name=first_name, last_name=last_name
        )
        # Log the user in after registration (optional)
        login(request, user)
        return JsonResponse({'success': True, 'user': serialize_user(user)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'success': True, 'user': serialize_user(user)})
    else:
        return JsonResponse({'error': 'Invalid username or password'}, status=401)


# ---------- USER DASHBOARD ----------
@login_required
def api_dashboard(request):
    price = FuelPrice.objects.first()
    wallet, _ = LitreWallet.objects.get_or_create(user=request.user)
    purchase_history = LitrePurchase.objects.filter(user=request.user).order_by('-created_at')[:5]
    expiring_lot = LitreLot.objects.filter(
        user=request.user, status='ACTIVE', expires_at__gt=timezone.now()
    ).order_by('expires_at').first()

    estimated_value = None
    if price:
        estimated_value = str(wallet.available_litres * price.price_per_litre)

    return JsonResponse({
        'user': serialize_user(request.user),
        'fuel_price': serialize_fuel_price(price),
        'wallet': serialize_wallet(wallet),
        'estimated_value': estimated_value,
        'recent_purchases': [serialize_purchase(p) for p in purchase_history],
        'expiring_lot': serialize_litre_lot(expiring_lot),
    })


# ---------- BUY LITRES (price info) ----------
@login_required
def api_buy_litres(request):
    price = FuelPrice.objects.first()
    return JsonResponse({
        'fuel_price': serialize_fuel_price(price),
    })


# ---------- INITIATE PAYMENT ----------
@login_required
@csrf_exempt
def api_initiate_payment(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    litres_raw = data.get('litres')
    try:
        litres = Decimal(litres_raw)
    except (TypeError, InvalidOperation):
        return JsonResponse({'error': 'Enter a valid number of litres'}, status=400)

    if litres <= 0:
        return JsonResponse({'error': 'Litres must be greater than zero'}, status=400)

    fuel_price = FuelPrice.objects.first()
    if not fuel_price:
        return JsonResponse({'error': 'Fuel price is currently unavailable'}, status=400)

    total_amount = litres * fuel_price.price_per_litre
    paystack_amount = int(total_amount * Decimal('100'))
    payment_reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"

    try:
        payment = initializePaystackPayment(
            request.user.email or request.user.username,
            paystack_amount,
            payment_reference
        )
        if not payment:
            return JsonResponse({'error': 'Payment initialization failed'}, status=500)

        InitializePaymentRecord.objects.create(
            user=request.user,
            reference=payment_reference,
            litres_to_purchase=litres,
            price_per_litre=fuel_price.price_per_litre,
            total_amount_to_pay=total_amount,
        )

        return JsonResponse({
            'success': True,
            'payment_reference': payment_reference,
            'payment_url': payment['payment_url'],
            'amount': str(total_amount),
        })
    except Exception as e:
        print("PAYMENT INIT ERROR:", e)
        return JsonResponse({'error': 'Payment initialization failed'}, status=500)


# ---------- VERIFY PAYMENT (callback) ----------
@login_required
def api_verify_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return JsonResponse({'error': 'Missing reference'}, status=400)

    try:
        payment_record = InitializePaymentRecord.objects.get(
            reference=reference,
            user=request.user
        )
        if payment_record.used:
            return JsonResponse({'error': 'Payment already used'}, status=400)

        # Verify with Paystack
        response = verifyPayment(reference)
        if not response:
            return JsonResponse({'error': 'Paystack verification failed'}, status=500)
        if not response.get('success'):
            return JsonResponse({'error': 'Payment not successful'}, status=400)

        # Compare amounts
        expected_kobo = int(payment_record.total_amount_to_pay * Decimal('100'))
        if response['amount'] != expected_kobo:
            return JsonResponse({'error': 'Amount mismatch'}, status=400)

        # Atomic creation of purchase and lot
        with transaction.atomic():
            purchase = LitrePurchase.objects.create(
                user=request.user,
                litres_bought=payment_record.litres_to_purchase,
                price_per_litre=payment_record.price_per_litre,
                payment_reference=reference,
            )
            lot = LitreLot.objects.create(
                user=request.user,
                purchase=purchase,
                litres_purchased=payment_record.litres_to_purchase,
                litres_remaining=payment_record.litres_to_purchase,
                price_per_litre=payment_record.price_per_litre,
                expires_at=timezone.now() + timedelta(days=90),
                status='ACTIVE',
            )
            payment_record.used = True
            payment_record.status = 'SUCCESS'
            payment_record.save(update_fields=['used', 'status'])

        return JsonResponse({
            'success': True,
            'purchase': serialize_purchase(purchase),
            'lot': serialize_litre_lot(lot),
        })
    except InitializePaymentRecord.DoesNotExist:
        return JsonResponse({'error': 'Payment record not found'}, status=404)
    except Exception as e:
        print("VERIFY ERROR:", e)
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# ---------- LITRE LOTS ----------
@login_required
def api_litre_lots(request):
    now = timezone.now()
    active_lots = LitreLot.objects.filter(
        user=request.user, status='ACTIVE',
        expires_at__gt=now, litres_remaining__gt=0
    ).select_related('purchase').order_by('expires_at')

    expired_lots = LitreLot.objects.filter(
        user=request.user
    ).filter(
        Q(status='EXPIRED') | Q(status='EXHAUSTED') | Q(expires_at__lte=now) | Q(litres_remaining=0)
    ).select_related('purchase').order_by('-expires_at')

    wallet, _ = LitreWallet.objects.get_or_create(user=request.user)

    return JsonResponse({
        'active_lots': [serialize_litre_lot(lot) for lot in active_lots],
        'expired_lots': [serialize_litre_lot(lot) for lot in expired_lots],
        'wallet': serialize_wallet(wallet),
        'available_litres': str(wallet.available_litres),
        'active_lot_count': active_lots.count(),
    })


# ---------- WALLET (just for completeness) ----------
@login_required
def api_wallet(request):
    wallet, _ = LitreWallet.objects.get_or_create(user=request.user)
    return JsonResponse({
        'wallet': serialize_wallet(wallet),
        'available_litres': str(wallet.available_litres),
    })


# ---------- REDEEM FUEL (station list) ----------
@login_required
def api_redeem_info(request):
    stations = Station.objects.filter(is_active=True).order_by('name')
    wallet, _ = LitreWallet.objects.get_or_create(user=request.user)
    return JsonResponse({
        'stations': [serialize_station(s) for s in stations],
        'wallet': serialize_wallet(wallet),
        'available_litres': str(wallet.available_litres),
    })


# ---------- GENERATE QR ----------
@login_required
@csrf_exempt
def api_generate_qr(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    litres_raw = data.get('litres')
    station_id = data.get('station_id')

    wallet, _ = LitreWallet.objects.get_or_create(user=request.user)
    stations = Station.objects.filter(is_active=True).order_by('name')

    try:
        litres = Decimal(litres_raw)
    except (TypeError, InvalidOperation):
        return JsonResponse({'error': 'Enter a valid number of litres'}, status=400)

    if litres <= 0:
        return JsonResponse({'error': 'Litres must be greater than zero'}, status=400)

    if litres > wallet.available_litres:
        return JsonResponse({
            'error': f'You only have {wallet.available_litres}L available'
        }, status=400)

    station = Station.objects.filter(id=station_id, is_active=True).first()
    if not station:
        return JsonResponse({'error': 'Please select a valid station'}, status=400)

    # Create redemption (reservation)
    redemption = fuelRedemption.objects.create(
        user=request.user,
        station=station,
        litres_redeemed=litres,
        qr_expires_at=timezone.now() + timedelta(minutes=10),
        status='PENDING',
    )

    confirm_url = request.build_absolute_uri(
        reverse('api-attendant-confirm', kwargs={'qr_code': redemption.qr_code})
    )

    # Generate QR image (base64)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(confirm_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B3D2E", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return JsonResponse({
        'success': True,
        'redemption': serialize_redemption(redemption),
        'qr_image_base64': qr_base64,
        'verification_code': redemption.verificaton_code,
        'confirm_url': confirm_url,
        'seconds_remaining': int((redemption.qr_expires_at - timezone.now()).total_seconds()),
    })


# ---------- QR EXPIRED ----------
@login_required
def api_qr_expired(request, redemption_id=None):
    redemption = None
    if redemption_id:
        redemption = fuelRedemption.objects.filter(id=redemption_id, user=request.user).first()
        if redemption and redemption.status == 'PENDING' and redemption.is_expired:
            redemption.status = 'EXPIRED'
            redemption.save(update_fields=['status'])
    return JsonResponse({
        'redemption': serialize_redemption(redemption) if redemption else None,
    })


# ---------- ATTENDANT PORTAL ----------
@staff_member_required
@csrf_exempt
def api_attendant_portal(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        code = data.get('verification_code', '').strip()
        if not code:
            return JsonResponse({'error': 'Enter a verification code'}, status=400)

        now = timezone.now()
        candidates = fuelRedemption.objects.filter(
            status='PENDING',
            qr_expires_at__gt=now
        )

        match = None
        for redemption in candidates:
            if redemption.verificaton_code == code:
                match = redemption
                break

        if match:
            return JsonResponse({
                'success': True,
                'redemption': serialize_redemption(match),
                'redirect_url': reverse('api-attendant-confirm', kwargs={'qr_code': match.qr_code}),
            })
        else:
            return JsonResponse({'error': 'No matching pending redemption found'}, status=404)

    # GET – return recent redemptions
    recent = fuelRedemption.objects.filter(
        redeemed_by=request.user, status='REDEEMED'
    ).order_by('-redeemed_at')[:5]
    return JsonResponse({
        'recent_redemptions': [serialize_redemption(r) for r in recent],
    })


# ---------- ATTENDANT CONFIRM ----------
@staff_member_required
@csrf_exempt
def api_attendant_confirm(request, qr_code):
    redemption = fuelRedemption.objects.filter(qr_code=qr_code).first()
    if not redemption:
        return JsonResponse({'error': 'Redemption not found'}, status=404)

    # Check expiration and status
    if redemption.status == 'PENDING' and redemption.is_expired:
        redemption.status = 'EXPIRED'
        redemption.save(update_fields=['status'])

    if redemption.status != 'PENDING':
        return JsonResponse({
            'error': f'This redemption is {redemption.get_status_display()} and can no longer be confirmed.'
        }, status=400)

    if request.method == 'POST':
        litres_to_deduct = redemption.litres_redeemed
        now = timezone.now()

        try:
            with transaction.atomic():
                active_lots = LitreLot.objects.select_for_update().filter(
                    user=redemption.user,
                    status='ACTIVE',
                    expires_at__gt=now,
                    litres_remaining__gt=0
                ).order_by('expires_at')

                remaining = litres_to_deduct
                for lot in active_lots:
                    if remaining <= 0:
                        break
                    deduct = min(lot.litres_remaining, remaining)
                    lot.litres_remaining -= deduct
                    remaining -= deduct
                    if lot.litres_remaining <= 0:
                        lot.status = 'EXHAUSTED'
                    lot.save(update_fields=['litres_remaining', 'status'])

                if remaining > 0:
                    raise ValueError('User no longer has enough litres available.')

                redemption.status = 'REDEEMED'
                redemption.redeemed_by = request.user
                redemption.redeemed_at = now
                redemption.save(update_fields=['status', 'redeemed_by', 'redeemed_at'])

            return JsonResponse({
                'success': True,
                'redemption': serialize_redemption(redemption),
                'redirect_url': reverse('api-attendant-success', kwargs={'redemption_id': redemption.id}),
            })
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An error occurred'}, status=500)

    # GET – show redemption info
    return JsonResponse({
        'redemption': serialize_redemption(redemption),
    })


# ---------- ATTENDANT SUCCESS ----------
@staff_member_required
def api_attendant_success(request, redemption_id):
    redemption = fuelRedemption.objects.filter(id=redemption_id).first()
    return JsonResponse({
        'redemption': serialize_redemption(redemption) if redemption else None,
    })


# ---------- ADMIN: PRICE MANAGEMENT ----------
@staff_member_required
def api_admin_price(request):
    if request.method == 'GET':
        current = FuelPrice.objects.first()
        history = FuelPrice.objects.all()[:20]  # limit for performance
        return JsonResponse({
            'current': serialize_fuel_price(current),
            'history': [serialize_fuel_price(p) for p in history],
        })
    elif request.method == 'POST' and request.user.is_superuser:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        new_price = data.get('price_per_litre')
        if not new_price:
            return JsonResponse({'error': 'Price must be provided'}, status=400)
        try:
            price_dec = Decimal(new_price)
        except InvalidOperation:
            return JsonResponse({'error': 'Price must be a valid number'}, status=400)

        FuelPrice.objects.create(price_per_litre=price_dec, set_by=request.user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Method not allowed or insufficient permissions'}, status=405)


# ---------- ADMIN: STATIONS ----------
@staff_member_required
def api_admin_stations(request):
    if request.method == 'GET':
        all_stations = Station.objects.all().order_by('name')
        return JsonResponse({
            'stations': [serialize_station(s) for s in all_stations],
        })
    elif request.method == 'POST' and request.user.is_superuser:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        action = data.get('action')
        if action == 'toggle':
            station_id = data.get('station_id')
            station = Station.objects.filter(id=station_id).first()
            if station:
                station.is_active = not station.is_active
                station.save()
                return JsonResponse({
                    'success': True,
                    'station': serialize_station(station),
                    'message': f'"{station.name}" is now {"active" if station.is_active else "inactive"}.'
                })
            else:
                return JsonResponse({'error': 'Station not found'}, status=404)
        else:
            # Add new station
            name = data.get('name', '').strip()
            address = data.get('address', '').strip()
            code = data.get('code', '').strip()
            if not name or not code:
                return JsonResponse({'error': 'Name and code are required'}, status=400)
            if not code.isdigit():
                return JsonResponse({'error': 'Code must be numeric'}, status=400)
            try:
                station = Station.objects.create(name=name, code=code, address=address)
                return JsonResponse({'success': True, 'station': serialize_station(station)})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed or insufficient permissions'}, status=405)


# ---------- ADMIN: USER MANAGEMENT ----------
@staff_member_required
def api_admin_users(request):
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0)

    all_users = User.objects.all().order_by('-date_joined')
    paginator = Paginator(all_users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return JsonResponse({
        'users': [serialize_user(u) for u in page_obj],
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'new_users_this_month': User.objects.filter(date_joined__gte=start_of_month).count(),
    })
"""
    create_file(os.path.join(api_dir, 'views.py'), views_content)

    # ========== api/urls.py ==========
    urls_content = """from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.api_register, name='api-register'),
    path('login/', views.api_login, name='api-login'),
    path('dashboard/', views.api_dashboard, name='api-dashboard'),
    path('buy/litres/', views.api_buy_litres, name='api-buy-litres'),
    path('initiate-payment/', views.api_initiate_payment, name='api-initiate-payment'),
    path('verify-payment/', views.api_verify_payment, name='api-verify-payment'),
    path('litre-lots/', views.api_litre_lots, name='api-litre-lots'),
    path('wallet/', views.api_wallet, name='api-wallet'),
    path('redeem/', views.api_redeem_info, name='api-redeem'),
    path('generate-qr/', views.api_generate_qr, name='api-generate-qr'),
    path('qr-expired/<int:redemption_id>/', views.api_qr_expired, name='api-qr-expired'),
    path('attendant/', views.api_attendant_portal, name='api-attendant-portal'),
    path('attendant/confirm/<uuid:qr_code>/', views.api_attendant_confirm, name='api-attendant-confirm'),
    path('attendant/success/<int:redemption_id>/', views.api_attendant_success, name='api-attendant-success'),
    path('admin/price/', views.api_admin_price, name='api-admin-price'),
    path('admin/stations/', views.api_admin_stations, name='api-admin-stations'),
    path('admin/users/', views.api_admin_users, name='api-admin-users'),
]
"""
    create_file(os.path.join(api_dir, 'urls.py'), urls_content)

    print("\n✅ API files created successfully!")
    print("\nNext steps:")
    print("1. Install django-cors-headers: pip install django-cors-headers")
    print("2. Add 'corsheaders' to INSTALLED_APPS and MIDDLEWARE in settings.py")
    print("3. Set CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS for your React frontend.")
    print("4. In your main urls.py, add: path('api/', include('api.urls'))")
    print("5. Ensure you have the necessary models and utils_pay.py in place.")
    print("\nYou can now use these API endpoints with your React frontend.")


if __name__ == '__main__':
    main()