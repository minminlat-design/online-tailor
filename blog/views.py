from django.shortcuts import get_object_or_404, render
from .models import Post




def post_list(request):
    posts = Post.published.all()
    return render(
        request,
        'blog/post/list.html',
        {'posts': posts}
    )




def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, 
            slug=post,
            publish__year=year,
            publish__month=month,
            publish__day=day)
   
    
    return render(
        request, 
        'blog/post/detail.html', 
        {
        'post': post,
        
    }
        )
