from django.shortcuts import render,redirect,get_object_or_404

# Create your views here.
from django.http import HttpResponse,HttpRequest,HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from .models import FuelPrice
from decimal import Decimal
from .models import Station, LitrePurchase, LitreWallet,LitreLot,initializePaymentMethod
from django.db import IntegrityError, transaction
import uuid
from .utils_pay import initializePayment,verifyPayment
from datetime import timedelta, timezone
import traceback
# Create your views here.



def loginView(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            error = "Inavlid eamil/Passowrd"
            return render(request, "login.html", {"error":error})
    
        try:
            user = authenticate(request, username=email, password=password)
            if not user :
                raise Exception("User Crrednetials not valid")
        
            login(request,user)
            
            if user.is_superuser or user.is_staff:
                return redirect('/staff/price-management/')
            else:
                return redirect("/dashboard/")
            
        except Exception as e:
            return render(request, 'login.html', {'error':str(e)})
    return render(request,'login.html',{})



def registerView(request):
    
    # get request, post request 
    if request.method == "POST":
        # PROCESS POST REQUEST IN HERE 
        email = request.POST.get('email')
        # password2 = request.POST.get('password2')
        password1 = request.POST.get('password')

        # validate the data 
        if not email or not password1 :
            # prevent them from signing up etc 
            error = "all details must be provided"
            return render(request,'signup.html',{"error": error, 'success': None})

        if len(password1) < 8:
            # prevent them from signing up etc 
            error = "password is too short"
            return render(request,'signup.html',{"error": error, 'success': None})

        # if password1 != password2:
        #     # prevent them from signing up etc 
        #     error = "password do not match"
        #     return render(request,'register.html',{"error": error, 'success': None})
        try:
            user = User.objects.create_user(username=email, email=email, password=password1)
            user.save()
            return redirect('user-login')
        except Exception as e : 
            pass 

    return render(request,'signup.html',{"error":None , "success":None})

@login_required(login_url='user-login')


@login_required(login_url='user-login')
def adminPriceManagementView(request:HttpRequest):
    if not request.user.is_superuser:
        return redirect("/dashboard/")
    error = None
    success = None
    if request.method == "POST":
        new_price:str = request.POST.get("price")
        if not new_price:
            error ="a new price must be set"
        elif not new_price.isdigit:
            error = "price must be a digit"
        else:
            #process the data
            price = Decimal(new_price)
            try:
                fuel_price = FuelPrice.objects.create(price_per_litre=price, set_by =request.user)
                fuel_price.save()
                success = f'Price updated successfully to {fuel_price.price_per_litre}'
            except Exception as e:
                error = str(e)
    current_price = FuelPrice.objects.first()
    price_history = FuelPrice.objects.all()
    return render(request, "admin_price_management.html",{"price":current_price, "error": error, "success":success, "price_history":price_history})


@login_required(login_url='user-login')
def adminStationView(request:HttpRequest):
    if not request.user.is_superuser:
        return redirect("/dashboard/")
    stations = Station.objects.all()
    return render(request, "admin_station.html",{'stations':stations})

@login_required(login_url='user-login')
def adminAddStation(request:HttpRequest):
    if not request.user.is_superuser:
        return redirect("/dashboard/")
    error = None
    success = None
    if request.method == "POST":
        name = request.POST.get("station-name")
        address = request.POST.get("station-address")
        code =request.POST.get("code")
        is_active = request.POST.get("is_active") == "on"
        # success()
        
        if not name or not address or not code:
            error = "Name, address and code are all required"
            
        else:
            try:
                station_name = Station.objects.create(name = name,address = address, code=code,is_active = is_active)
                
                return redirect("admin-add-newstation")
            except IntegrityError:
                            error = "A station with that code already exist"
            except Exception as e:
                error = str(e)
            
                
    return render(request, "addStations.html",{"error":error, "success":success})

def buyLitreView(request:HttpRequest):
    if request.user.is_superuser:
        return redirect("admin-price-management")
    current_price = FuelPrice.objects.first()
    return render(request, "buylitre.html",{'current_price':current_price})

@login_required(login_url='user-login')
def proceedToPaystack(request:HttpRequest):
    if request.user.is_superuser:
        return redirect("admin-price-management")
    
    if request.method != "POST":
        print('not a post')
        return redirect('buy-litre')
    
    litre_raw = request.POST.get('litres')
    # price_raw = request.POST.get('price_per_litre')
    
    try:
        litres = Decimal(litre_raw)
        # price_per_litre = Decimal(price_raw)
        
    except(TypeError):
        return render(request, "buylitre.html", {
            "current_price" : FuelPrice.objects.first(),
            "error" : "Enter a valid number of litres." 
        })
        
        
    if litres <= 0:
        return render(request, "buylitre.html", {
        "current_price" : FuelPrice.objects.first(),
        "error" : "Enter a valid number of litres." 
        })
    
    fuel_price = FuelPrice.objects.first()

    if fuel_price is None:
        return render(request, "user/buylitres.html", {
            "price": None,
            "error": "Fuel price is currently unavailable.",
        })

    price_per_litre = fuel_price.price_per_litre
    
    total_amount = litres * price_per_litre
    
    paystack_amount = int(total_amount * Decimal("100"))
              
    payment_refrence = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    try:
        is_valid = initializePayment(request.user.email or request.user.username, paystack_amount, payment_refrence)
        if not is_valid:
            return redirect('user-buylitre')
            #DOCUMENT THE RECOEDS DOWN
        initializePaymentMethod(user=request.user, reference = payment_refrence, litre_to_purchase = litres, total_amount_to_pay = total_amount)
        return redirect(is_valid['payment_url'])  
    except Exception as e : 
        print('PAYMENT INITIALIZATION:', e)
        return redirect('/buylitre/')
    
@login_required(login_url='user-login')
def purchaseCreateView(request: HttpRequest):
    if request.user.is_superuser:
        return redirect('/staff/pricemanage/')

    

    # payment_reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    reference = request.GET.get('reference')
    if not reference:
        return redirect('/failure/')
    # verify from paystack first 
    try :
        payment_record = initializePaymentMethod.objects.get(
            reference=reference,
            user=request.user
        )
        
        if payment_record.used:
            return redirect("/failure/")
        
        response = verifyPayment(reference)
        
        if not response :
            return redirect('/failure/')
        
        if response['success'] == False :
            return redirect('/failure/')
        
        paystack_amount = response['amount']
        
        expected_amount_in_kobo = int(
            payment_record.total_amount_to_pay * Decimal("100")
        )
        if paystack_amount != expected_amount_in_kobo:
            print(
                "PAYMENT AMOUNT MISMATCH:",
                paystack_amount,
                expected_amount_in_kobo,
            )
            return redirect('/failure/')
        
        if LitrePurchase.objects.filter(
            reference=reference
        ).exists():
            return redirect('/failure/')
        
        with transaction.atomic():

            purchase = LitrePurchase.objects.create(
                user=request.user,
                litres_bought=payment_record.litres_to_purchase,
                price_per_litre=payment_record.price_per_litre,
                payment_reference=payment_record.reference,
            )

            litre_lot = LitreLot.objects.create(
                user=request.user,
                purchase=purchase,
                litres_purchased=payment_record.litres_to_purchase,
                litres_remaining=payment_record.litres_to_purchase,
                price_per_litre=payment_record.price_per_litre,
                expires_at=timezone.now() + timedelta(days=90),
                status="ACTIVE",
            )

            # Mark payment as consumed only after
            # purchase + lot have successfully been created.
            payment_record.used = True
            payment_record.status = "SUCCESS"
            payment_record.save(
                update_fields=["used", "status"]
            )
        return redirect(
            f"/successview/{litre_lot.id}"
        )

    except initializePaymentMethod.DoesNotExist:
        print("PAYMENT RECORD NOT FOUND")
        return redirect("/failure/")

    except Exception as e:
        print("========== PURCHASE ERROR ==========")
        print("ERROR:", e)
        traceback.print_exc()
        print("====================================")
        return redirect("/error/")

        
        


def purchaseSuccessView(request:HttpRequest, pid):
    if request.user.is_superuser:
        return redirect("admin-price-management")
    # price = FuelPrice.objects.first()
    purchase = get_object_or_404(
        LitrePurchase,
        id = pid,
        user=request.user
    )
    
    litre_lot = get_object_or_404(
        LitreLot,
        purchase = purchase,
        User = request.user
    )
    
    context = {
        "purchase" : purchase,
        "litre_lot" : litre_lot
    }
    return render (request,"10-purchase-success.html", context)

def dashBoardView(request:HttpRequest):
    if request.user.is_superuser:
        return redirect("admin-price-management")
    current_price = FuelPrice.objects.first()
    price_history = FuelPrice.objects.all()
    recent_purchase = LitrePurchase.objects.select_related('user').order_by('-created_at')[:5]
    return render(request, "dashboard.html",{
        'current_price':current_price,
        'price_history': price_history,
        'recent_purchase': recent_purchase})

def litreLotView(request:HttpRequest):
    if not request.user.is_superuser:
        return redirect("admin-price-management")
    lots = LitreLot.objects.filter(
        user = request.user
    )
    
    active_lots = lots.filter(
        status = "ACTIVE",
        expires_at_gt = timezone.now(),
        litres_remaining_gt = 0
    ).order_by("expires_at")
    
    expired_lots = lots.filter(
        status = "EXPIRED"
    ).order_by("expires_at")
    
    wallet, created = LitreWallet.objects.get_or_create(
        user=request.user
    )
    
    context = {
        "lots":lots,
        "total_lots":lots.count(),
        "active_lots":active_lots,
        "active_lots_count":active_lots.count,
        "wallet":wallet,
        "expried_lots" : expired_lots
    }
    return render(request, "litre-lots.html",context)

@login_required(login_url='user-login')
def fromPayStackRedirectView(request:HttpRequest):
    if request.user.is_superuser:
        return redirect('admin-price-management')
    
    return render(request, '10-purchase-success.html', {"user_lot_purchased":None})