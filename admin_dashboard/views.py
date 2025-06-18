from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from admin_dashboard.forms import OrderStatusForm, OrderItemMeasurementForm
from orders.models import Order, OrderItem
from django.db.models import Count, Sum
from django.shortcuts import redirect
from django.forms import modelformset_factory
from django.contrib import messages









@staff_member_required
def dashboard_home(request):
    order_counts = Order.objects.values('status').annotate(count=Count('id'))
    total_revenue = Order.objects.filter(paid=True).aggregate(Sum('total_price'))['total_price__sum'] or 0

    return render(request, 'admin_dashboard/dashboard_home.html', {
        'order_counts': order_counts,
        'total_revenue': total_revenue,
    })


@staff_member_required
def order_list(request):
    orders = Order.objects.all().order_by('-created')
    return render(request, 'admin_dashboard/order_list.html', {'orders': orders})







@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    OrderItemFormSet = modelformset_factory(
        OrderItem, 
        form=OrderItemMeasurementForm, 
        extra=0,
        can_delete=False
    )

    if request.method == 'POST':
        status_form = OrderStatusForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, queryset=OrderItem.objects.filter(order=order))

        if not status_form.is_valid():
            print("Status form errors:", status_form.errors)
        if not formset.is_valid():
            print("Formset errors:", formset.errors)

        if status_form.is_valid() and formset.is_valid():
            status_form.save()
            formset.save()
            return redirect('admin_dashboard:order_detail', order_id=order.id)

    else:
        status_form = OrderStatusForm(instance=order)
        formset = OrderItemFormSet(queryset=OrderItem.objects.filter(order=order))

    return render(request, 'admin_dashboard/order_detail.html', {
        'order': order,
        'status_form': status_form,
        'formset': formset,
    })
