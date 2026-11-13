from django.shortcuts import render, get_object_or_404, redirect
from .models import Banner, Category, Product, CartItem, Order, OrderItem, Place, Brand, Rating
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .ajax import is_ajax
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from decimal import Decimal
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.core.cache import cache
from datetime import timedelta
from django.utils.http import url_has_allowed_host_and_scheme



def index(request):
    if request.has_place:
        place_id = request.place_id

        products = (
            Product.objects
            .filter(
                place_id=place_id,
                is_top=True,
            )
            .order_by("created_at")[:12]
        )

        cache_key = f"banners_place_{place_id}"

        banners = cache.get(cache_key)

        if banners is None:
            banners = list(
                Banner.objects
                .filter(place_id=place_id)
                .order_by("-created_at")
            )

            cache.set(
                cache_key,
                banners,
                60 * 60 * 24 * 30
            )

    else:
        products = (
            Product.objects
            .filter(is_top=True)
            .order_by("created_at")[:11]
        )

        banners = (
            Banner.objects
            .order_by("-created_at")[:5]
        )

    context = {
        "products": products,
        "banners": banners,
    }

    return render(request, "cart/index.html", context)


def product_detail(request, slug):
    try:
        product = get_object_or_404(
            Product.objects.select_related('category').filter(place_id=request.place_id),
            slug=slug
        )
        specifications = product.specifications.order_by('-id')
    except Exception as e:
        return redirect('cart:home')

    context = {
        'product': product,
        'specifications': specifications
    }
    return render(request, 'cart/product_detail.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(place_id=request.place_id).order_by('id')

    paginator = Paginator(products, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    products_count = paginator.count

    context = {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
        'products_count': products_count
    }
    return render(request, 'cart/category_detail.html', context)


@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)

    user = request.user if request.user.is_authenticated else None
    device_id = getattr(request, 'device_id', None)

    brand = request.POST.get('brand')
    model_name = request.POST.get('model')
    year = request.POST.get('year')
    car_number_type = request.POST.get('car_number_type')
    license_plate = str(request.POST.get('car_number')).strip().replace(" ", "")
    casting_type = request.POST.get('casting_type')
    engine = request.POST.get('engine')


    if user:
        lookup = {'user': user}
    else:
        lookup = {'device_id': device_id, 'user__isnull': True}

    if product.category.requires_parameters:
        cart_item, created = CartItem.objects.get_or_create(
            product=product,
            brand=brand,
            model=model_name,
            year=year,
            car_number_type=car_number_type,
            license_plate=license_plate,
            casting_type=casting_type,
            engine=engine,    
            defaults={'quantity': 1},
            **lookup
        )
    else:
        cart_item, created = CartItem.objects.get_or_create(
            product=product,
            brand=brand,
            model=model_name,
            year=year,
            car_number_type=car_number_type,
            license_plate=license_plate,
            casting_type=casting_type,
            engine=engine,
            defaults={'quantity': 1},
            **lookup
        )

    total_quantity = CartItem.objects.filter(**lookup).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    return JsonResponse({
        'status': 'success',
        'created': created,         
        'exists': not created,      
        'total': total_quantity,    
        'item_quantity': cart_item.quantity  
    })
        

def cart(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related("product")
    else:
        cart_items = CartItem.objects.filter(device_id=request.device_id).select_related("product")

    context = {
        'cart_items': cart_items
    }
    return render(request, 'cart/cart.html', context)



def increase_quantity(request):
    if request.method == "POST":
        cart_item = get_object_or_404(
            CartItem,
            id=request.POST.get("id")
        )

        cart_item.quantity += 1
        cart_item.save()

        
        filters = Q()
        if request.user.is_authenticated:
            filters |= Q(user=request.user)

        device_id = request.device_id  
        if device_id:
            filters |= Q(device_id=device_id)

        total_count = (
            CartItem.objects
            .filter(filters)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        if is_ajax(request):
            return JsonResponse({
                "quantity": cart_item.quantity,
                "total_count": total_count,
            })

        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
        


def decrease_quantity(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request"},
            status=400
        )

    cart_item = get_object_or_404(
        CartItem,
        id=request.POST.get("id")
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save(update_fields=["quantity"])

    filters = Q(device_id=request.device_id)

    if request.user.is_authenticated:
        filters |= Q(user=request.user)

    total_count = (
        CartItem.objects
        .filter(filters)
        .aggregate(total=Sum("quantity"))["total"]
        or 0
    )

    if is_ajax(request):
        return JsonResponse({
            "quantity": cart_item.quantity,
            "total_count": total_count
        })

    return JsonResponse(
        {"error": "AJAX request required"},
        status=400
    )


def remove_from_cart(request):
    if request.method == "POST":
        cart_item = get_object_or_404(
            CartItem,
            id=request.POST.get("id")
        )

        cart_item.delete()

        filters = Q()
        if request.user.is_authenticated:
            filters |= Q(user=request.user)

        device_id = request.device_id
        if device_id:
            filters |= Q(device_id=device_id)

        total_count = (
            CartItem.objects
            .filter(filters)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        
        if is_ajax(request):
            return JsonResponse({
                "total_count": total_count
            })

        return JsonResponse({"status": "ok", "total_count": total_count})

    return JsonResponse({"error": "Invalid request"}, status=400)


def search_item(request):
    query = request.GET.get('query', '').strip()
    place = None

    if request.has_place:
        place = Place.objects.get(
            id=request.place_id
        )

    products = Product.objects.none()

    if query and place is not None:
        products = (
            Product.objects
            .filter(
                place=place
            )
            .filter(
                Q(title_tm__icontains=query) |
                Q(title_ru__icontains=query)
            )
            .select_related('category')
        )

    paginator = Paginator(products, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'cart/search.html',
        {
            'query': query,
            'products': page_obj,
            'page_obj': page_obj
        }
    )


def create_order(request, user=None, status=None):
    cart_filter = Q()
    place = None

    if user is None or not user.is_authenticated:
        return 401
    
    if not status:
        return "status"

    if request.has_place:
        place = Place.objects.get(id=request.place_id)

    cart_filter |= Q(user=user)

    cart_items = CartItem.objects.filter(cart_filter)

    if not cart_items.exists():
        return None

    with transaction.atomic():

        order = Order.objects.create(
            place=place,
            user=user,
            address="address",
            status=status
        )

        total = Decimal("0.00")

        for item in cart_items.select_related("product"):

            price = item.product.price or Decimal("0.00")

            try:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_title=item.product.title_tm,
                    product_price=price,
                    quantity=item.quantity,
                    brand=item.brand,
                    year=item.year,
                    model=item.model,
                    engine=item.engine,
                    casting_type=item.casting_type,
                    car_number_type=item.car_number_type,
                    license_plate=item.license_plate
                )
            except Exception as e:
                print(str(e))
                return "duplicate"

            total += price * item.quantity

        order.total_price = total
        order.save(update_fields=["total_price"])

        cart_items.delete()

    return order



def checkout_order(request):
    if request.method == "POST":

        user = request.user if request.user.is_authenticated else None

        order = create_order(request, user=user, status="success")

        if order is None:
            messages.error(request, "Sebet boş")
            return redirect("cart:cart")  # или твой url
        elif order == "address":
            messages.error(request, "Adresi dolduryň")
            return redirect("cart:cart")
        elif order == 'status':
            return redirect("cart:cart")
        elif order == 401:
            messages.error(request, "Ulgamyň içine giriň")
            return redirect("cart:cart")  # или твой url
        elif order == 'duplicate':
            messages.error(request, "Hyzmaty gaýtadan döredip bolmaýar. Sargyt bar")
            return redirect("cart:cart")

        messages.success(request, "Hyzmat üstünlikli döredildi siz bilen habarlaşylar")

        return redirect("cart:cart")

    return redirect("cart:cart")



def orders(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Ulgamyň içine giriň")
        return redirect('/')
    
    orders = (
        request.user.orders
        .prefetch_related("items")
        .order_by("-created_at")
    )

    return render(request, "cart/orders.html", {
        "orders": orders
    })



def product_list(request):
    products = Product.objects.all()

    if getattr(request, 'has_place', False) and getattr(request, 'place_id', None):
        products = products.filter(place_id=request.place_id).order_by("id")
    else:
        products = products.order_by("-id")

    products = products.select_related('category')

    paginator = Paginator(products, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "cart/product_list.html", {
        "products": page_obj,
        "page_obj": page_obj,
    })


def about_company(request):
    return render(request, 'cart/about_company.html', {})


def set_place(request):
    place_id = request.POST.get("place_id")

    response = JsonResponse({
        "success": True
    })

    response.set_cookie(
        "place_id",
        place_id,
        max_age=60 * 60 * 24 * 30 * 3,  # 3 months
        httponly=False,
        secure=False,
        samesite="Lax",
    )

    return response


@require_POST
def set_location(request):
    if request.method == 'POST':
        next_url = request.POST.get('next_url') or '/'

        url_is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        
        if not url_is_safe:
            next_url = '/'

        response = redirect(next_url)
        response.delete_cookie('place_id')
        
        return response

    return redirect('/')


def get_by_brand(request):
    brand = Brand.objects.get(
        id=request.POST.get("brand_id")
    )

    children = list(
        brand.children.values(
            "id",
            "title"
        )
    )

    return JsonResponse(children, safe=False)


@login_required
def add_review(request):
    try:
        if request.method == 'POST':
            rating = request.POST.get('r_rating') or request.POST.get('r_rating-sm')
            comment = request.POST.get('r_comment') or request.POST.get('r_comment-sm')
            user = request.user

            new_rating = Rating.objects.create(
                user=user,
                description=comment,
                star=rating,
                status='pending'
            )
            new_rating.save()
            messages.success(request, f'Siziň bahaňyz üstünlikli goşuldy. Siziň bahaňyz administrator tarapyndan barlanandan soňra görkeziler.')
            return redirect('/')
        else:
            messages.error(request, f'Gosmak üçin ýalňyş usul ulanyldy. Siziň bahaňyz goşulmandy.')
            return redirect('/')
    except Exception as e:
        messages.error(request, f'{e}')
        return redirect('/')


@login_required
def add_review_product(request):
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            rating = request.POST.get('rating_star_product') 
            comment = request.POST.get('comment')
            user = request.user

            if not rating or rating == '0':
                messages.error(request, 'Baha goýmagyňyzy haýyş edýäris (ýyldyz saýlaň).')
                return redirect(request.META.get('HTTP_REFERER', '/'))


            product = Product.objects.get(id=product_id)

            new_rating = Rating.objects.create(
                user=user,
                product=product,
                description=comment,
                star=rating,
                status='pending'
            )
            new_rating.save()
            
            messages.success(request, 'Siziň bahaňyz üstünlikli goşuldy. Siziň bahaňyz administrator tarapyndan barlanandan soňra görkeziler.')
            
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
        except Exception as e:
            messages.error(request, f'Ýalňyşlyk: {e}')
            return redirect(request.META.get('HTTP_REFERER', '/'))
    else:
        messages.error(request, 'Gosmak üçin ýalňyş usul ulanyldy. Siziň bahaňyz goşulmandy.')
        return redirect(request.META.get('HTTP_REFERER', '/'))


def reviews(request):
    ratings = Rating.objects.filter(status="success").order_by("-created_at")
    return render(request, 'cart/reviews.html', {"ratings": ratings})

