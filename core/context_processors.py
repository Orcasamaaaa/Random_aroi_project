from .models import Restaurant

def user_restaurant(request):
    if request.user.is_authenticated:
        restaurant = Restaurant.objects.filter(owner=request.user).first()
    else:
        restaurant = None
    return {'restaurant': restaurant}
