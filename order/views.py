from django.shortcuts import HttpResponse, render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.views import View
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .pdfcreator import renderPdf
from django.conf import settings
import razorpay

def order_create(request):
	print(settings.RAZORPAY_KEY_ID)
	cart = Cart(request)
	if not request.user.is_authenticated:
		messages.error(request,"You need to log in to proceed to checkout.")
		return redirect('store:signin')
	if len(cart)==0:
		return redirect('store:books')
	customer = get_object_or_404(User, id=request.user.id)
	form = OrderCreateForm(request.POST or None, initial={"name": customer.first_name, "email": customer.email})
	if request.method == 'POST':
		if form.is_valid():
			order = form.save(commit=False)
			order.customer = User.objects.get(id=request.user.id)
			order.payable = cart.get_total_price()
			order.totalbook = len(cart) # len(cart.cart) // number of individual book
			order.save()
			try:
				client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
				data = {
					"amount": int(cart.get_total_price() * 100),  # Convert to paise
					"currency": "INR",
					"receipt": str(order.id)
					}
				razorpay_order = client.order.create(data=data)
				order.razorpay_order_id = razorpay_order['id']
				order.save()
			except Exception as e:
				messages.error(request, f"Error connecting to Razorpay:{str(e)}")
				order.delete()
				return redirect('cart:cart_details')
			for item in cart:
				OrderItem.objects.create(
					order=order, 
					book=item['book'], 
					price=item['price'], 
					quantity=item['quantity']
					)
				cart.clear()
				context = {
					'order': order,
					'razorpay_order_id': razorpay_order['id'],
					'razorpay_merchant_key': settings.RAZORPAY_KEY_ID
					}
				return render(request, 'order/razorpay_payment.html', context)
		else:
			messages.error(request, "Fill out your information correctly.")
	return render(request, 'order/order.html', {"form": form})
			
def order_list(request):
	my_order = Order.objects.filter(customer_id = request.user.id).order_by('-created')
	paginator = Paginator(my_order, 5)
	page = request.GET.get('page')
	myorder = paginator.get_page(page)

	return render(request, 'order/list.html', {"myorder": myorder})

def order_details(request, id):
	order_summary = get_object_or_404(Order, id=id)

	if order_summary.customer_id != request.user.id:
		return redirect('store:index')

	orderedItem = OrderItem.objects.filter(order_id=id)
	context = {
		"o_summary": order_summary,
		"o_item": orderedItem
	}
	return render(request, 'order/details.html', context)

class pdf(View):
    def get(self, request, id):
        try:
            query=get_object_or_404(Order,id=id)
        except:
            Http404('Content not found')
        context={
            "order":query
        }
        article_pdf = renderPdf('order/pdf.html',context)
        return HttpResponse(article_pdf,content_type='application/pdf')
def payment_success(request, payment_id):
	try:
		order = Order.objects.get(razorpay_order_id=payment_id)
		order.paid = True
		order.save()
		return render(request, 'order/successfull.html', {'order': order})
	except Order.DoesNotExist:
		messages.error(request, "Order not found.")
		return redirect('store:index')