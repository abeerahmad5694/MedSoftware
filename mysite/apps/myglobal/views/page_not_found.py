
from django.shortcuts import render

def page_not_found(request):
    return render(request, 'myglobal/include/403.html')
