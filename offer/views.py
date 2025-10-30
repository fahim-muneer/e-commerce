from django.shortcuts import render, redirect, get_object_or_404
from .models import Offers
from .forms import AddOfferForm
from django.views import View
from django.views.generic import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import ValidationError


class OfferView(View):
    def get(self, request):
        search = request.GET.get('q')
        offer_type_filter = request.GET.get('type')
        
        offers = Offers.objects.all().order_by('-created_at')
        
        if search:
            offers = offers.filter(name__icontains=search)
        
        if offer_type_filter:
            offers = offers.filter(offer_type=offer_type_filter)
        
        page = request.GET.get('page', 1)
        paginator = Paginator(offers, 10)
        offers = paginator.get_page(page)
        
        context = {
            'offer': offers,
            'search_query': search,
            'type_filter': offer_type_filter
        }
        
        return render(request, 'offers/view_offer.html', context)


class AddOffer(View):
    def get(self, request):
        form = AddOfferForm()
        context = {'form': form}
        return render(request, 'offers/add_offer.html', context)
    
    def post(self, request):
        form = AddOfferForm(request.POST)
        
        if form.is_valid():
            try:
                offer = form.save(commit=False)
                offer.full_clean()
                offer.save()
                
                form.save_m2m()
                
                messages.success(request, f'Offer "{offer.name}" added successfully.')
                return redirect('offer_view')
                
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'offers/add_offer.html', {'form': form})
            except Exception as e:
                messages.error(request, f'Error adding offer: {str(e)}',extra_tags='add-offer')
                return render(request, 'offers/add_offer.html', {'form': form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}',extra_tags='add-offer')
            return render(request, 'offers/add_offer.html', {'form': form})


class UpdateOffer(UpdateView):
    model = Offers
    form_class = AddOfferForm
    template_name = "offers/update_offer.html"
    success_url = reverse_lazy('offer_view')

    def form_valid(self, form):
        try:
            offer = form.save(commit=False)
            offer.save()
            form.save_m2m()  


            messages.success(
                self.request, 
                f'Offer "{offer.name}" updated successfully.',
                extra_tags='offer_update' 
            )
            
            return redirect(self.success_url)

        except ValidationError as e:

            for error in e.messages:
                messages.error(
                    self.request, 
                    error,
                    extra_tags='offer_update'
                )
                print(f"error is {str(e)}")
            return self.form_invalid(form)

        except Exception as e:
            # --- FIX APPLIED HERE ---
            # Pass 'offer_update' as an extra tag along with the default 'error' tag.
            messages.error(
                self.request, 
                f'Error updating offer: {str(e)}',
                extra_tags='offer_update'
            )
            print(f"error is {str(e)}")
            return self.form_invalid(form)


class DeleteOffer(DeleteView):
    model = Offers
    template_name = "offers/delete_offer.html"
    success_url = reverse_lazy('offer_view')
    
    def delete(self, request, *args, **kwargs):
        offer = self.get_object()
        messages.success(request, f'Offer "{offer.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class OfferDetailView(View):
    """View to see which products/categories an offer is applied to"""
    def get(self, request, pk):
        offer = get_object_or_404(Offers, pk=pk)
        
        context = {
            'offer': offer,
            'applied_categories': offer.categories.all(),
            'applied_products': offer.products.all(),
        }
        
        return render(request, 'offers/offer_detail.html', context)

    

