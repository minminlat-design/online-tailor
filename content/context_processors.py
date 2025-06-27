# content/context_processors.py
from .models import StaticPage, SocialMediaLink

def navbar_static_pages(request):
    pages = StaticPage.objects.filter(published=True, show_in_navbar=True).order_by('order')
    return {'navbar_static_pages': pages}





def social_links(request):
    links = SocialMediaLink.objects.filter(visible=True)
    return {'social_links': links}
