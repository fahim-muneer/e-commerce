from django.shortcuts import render


def error_page(request):
    return render(request,'bughandler/errorpage.html')