from django.urls import path


from . import views

app_name = 'cart'
urlpatterns = [
    path('', views.index, name='home'),
    path('product/<slug>/', views.product_detail, name='product_detail'),
    path('add-to-cart/', views.add_to_cart, name='add-to-cart'),
    path('increase-quantity/', views.increase_quantity, name='increase-quantity'),
    path('decrease-quantity/', views.decrease_quantity, name='decrease-quantity'),
    path('remove-from-cart/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/', views.cart, name='cart'),
    path('search', views.search_item, name='search-item'),
    path('checkout-order/', views.checkout_order, name='checkout-order'),
    path('orders/', views.orders, name='orders'),
    path("set-place/", views.set_place, name="set_place"),
    path('product-list/', views.product_list, name='product-list'),
    path('set-location/', views.set_location, name='set-location'),
    path('about-company/', views.about_company, name='about-company'),
    path('category-detail/<slug>/', views.category_detail, name='category-detail'),
    path('get-by-brand/', views.get_by_brand, name='get-by-brand'),
    path('add-review/', views.add_review, name='add-review'),
    path('reviews/', views.reviews, name='reviews'),
    path('add-review-product/', views.add_review_product, name='add-review-product')
    #path('create-year/', views.create_years),
]