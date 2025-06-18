from django.shortcuts import render


def search_view(request):
    return render(request, 'search/search.html')
