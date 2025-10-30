from django.shortcuts import render,redirect
from django.views import View
from django.views.generic import UpdateView,DeleteView
from .forms import VarientsForm
from .models import Varient
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import *
from django.db.utils import *


class VarientsView(View):
    def get(self,request):
        search = request.GET.get("q")
        if search:
            varient=Varient.objects.filter(name__icontains=search)   # pylint: disable=no-member
        else:
            varient = Varient.objects.all() #pylint: disable=no-member
        page = 1
        if request.GET:
            page = request.GET.get('page', 1)

        user_paginator = Paginator(varient, 5)
        varient = user_paginator.get_page(page)
        page = 1
        if request.GET:
            page = request.GET.get('page', 1)

        user_paginator = Paginator(varient, 5)
        varient = user_paginator.get_page(page)
     
        context={
            'varient':varient
                }
        return render (request, 'varients/varients.html',context)





class AddVarients(View):
    def get(self, request):
        form = VarientsForm()
        return render(request, 'varients/add_varients.html', {'form': form})
    
    def post(self, request):
        form = VarientsForm(request.POST)
        
        if form.is_valid():
            try:
                variant = form.save(commit=False)
                variant.full_clean() 
                variant.save()
                
                messages.success(request, 'The variant was added successfully.',extra_tags='variant')
                return redirect('varient_list')
                
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, error)
                else:
                    messages.error(request, str(e),extra_tags='variant')
                return render(request, 'varients/add_varients.html', {'form': form})
                
            except IntegrityError:
                messages.error(request, 'A variant with this name already exists.',extra_tags='variant')
                return render(request, 'varients/add_varients.html', {'form': form})
                
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}',extra_tags='variant')
                return render(request, 'varients/add_varients.html', {'form': form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}',extra_tags='variant')
            return render(request, 'varients/add_varients.html', {'form': form})


class UpdateVarients(UpdateView):
    model = Varient
    fields = ['name']
    template_name = 'varients/update_varients.html'
    success_url = reverse_lazy('varient_list')
    
    def form_valid(self, form):
        try:
            variant = form.save(commit=False)
            variant.full_clean()
            variant.save()
            messages.success(self.request, f'Variant updated successfully.',extra_tags='variant-update')
            return redirect(self.success_url)
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(self.request, error)
            else:
                messages.error(self.request, str(e))
            return self.form_invalid(form)
        except IntegrityError:
            messages.error(self.request, 'A variant with this name already exists.',extra_tags='variant-update')
            return self.form_invalid(form)


class DeleteVarients(DeleteView):
    model = Varient
    template_name = 'varients/delete_varients.html'
    success_url = reverse_lazy('varient_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Variant deleted successfully.')
        return super().delete(request, *args, **kwargs)