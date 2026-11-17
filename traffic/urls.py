from django.urls import path
from traffic.views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
]