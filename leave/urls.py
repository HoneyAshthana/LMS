from django.urls import path
from leave.views import index_view

urlpatterns=[
    path('',index_view,name='index'),
    
    
]