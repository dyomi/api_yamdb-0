from django.contrib import admin

from .models import Category, Comment, CustomUser, Genre, Review, Title


admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(Genre)
admin.site.register(Review)
admin.site.register(Title)
