from django.shortcuts import render

# Create your views here.

def error_page(request):
    return render(request,'bughandler/errorpage.html')