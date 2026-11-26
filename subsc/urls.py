from django.urls import path
from . import views

urlpatterns = [
    # サブスク関連（利用者向け）
    path('subsc/register/', views.subsc_register, name='subsc_register'),
    path('subsc/update/', views.subsc_update, name='subsc_update'),
    path('subsc/cancel/', views.subsc_cancel, name='subsc_cancel'),

    # IC関連情報登録（利用者向け）
    path('ic/register/', views.ic_register, name='ic_register'),

    # 管理者向け一覧画面
    path('admin/users/', views.user_list, name='user_list'),
    path('admin/users/<str:link_id>/', views.user_detail, name='user_detail'),
    path('admin/movements/', views.movement_list, name='movement_list'),
]