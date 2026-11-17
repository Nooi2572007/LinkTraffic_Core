from django.urls import path
from subsc.views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
]