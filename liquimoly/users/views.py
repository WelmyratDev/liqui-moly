from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from .models import User
from datetime import timedelta
from cart.models import Place



@login_required
def logout_view(request):
    if request.method == 'POST':
        next = request.POST.get('next', '/')
        auth.logout(request)
        messages.success(request, "Siz ulgamdan çykdyňyz.")
        return redirect(next)
    return redirect('/')



def login_view(request):
    if request.method == "POST":
        fullname = request.POST.get("fullname")
        phone_number = request.POST.get("phone_number")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me") == "on"
        place_id = None

        if request.has_place:
            place_id = Place.objects.get(id=request.place_id)

        user = User.create_user_if_not_exists(place_id, fullname, phone_number, password)

        if user is None:
            messages.error(request, "Telefon belgisinde ýalňyşlyk.")
            return redirect("/")

        
        auth_user = auth.authenticate(
            request,
            username=user.phone_number,
            password=password
        )

        if auth_user is None:
            messages.error(request, "Nädogry maglumatlar.")
            return redirect("/")
        
        auth.login(request, auth_user)

        if remember_me:
            request.session.set_expiry(timedelta(days=30))
        else:
            request.session.set_expiry(0)

        next = request.POST.get("next", "/")
        messages.success(request, "Siz ulgamyň içine girdiňiz.")
        return redirect(next)

    return redirect("/")
