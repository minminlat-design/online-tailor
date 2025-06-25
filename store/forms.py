from django import forms
from .models import ReviewRating, ReviewReply



class ReviewRatingForm(forms.ModelForm):
    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']






class ReviewReplyForm(forms.ModelForm):
    class Meta:
        model = ReviewReply
        fields = ['reply']
