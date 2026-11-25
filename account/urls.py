from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    # 1. トップ・メイン・マイページ
    path('', views.top_view, name='top'),
    path('main/', views.main_view, name='main'),
    path('mypage/', views.mypage_view, name='mypage'),

    # 2. ログイン・ログアウト
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 3. アカウント新規登録
    path('register/', views.user_register_view, name='user_register'),
    path('register/confirm/', views.user_register_confirm_view, name='user_register_confirm'),
    path('register/done/', views.user_register_done_view, name='user_register_done'),

    # 4. アカウント変更
    path('update/', views.user_update_view, name='user_update'),
    path('update/confirm/', views.user_update_confirm_view, name='user_update_confirm'),
    path('update/done/', views.user_update_done_view, name='user_update_done'),

    # 5. アカウント削除
    path('archive/', views.user_archive_view, name='user_archive'),
    path('archive/done/', views.user_archive_done_view, name='user_archive_done'),

    # 6. パスワード再設定
    path('password_reset/', views.password_reset_link_view, name='password_reset_link'),
    path('password_reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password_reset/<str:token>/', views.password_reset_view, name='password_reset'),

    # 7. 郵便番号検索API
    path('api/zipcode/', views.zipcode_search_api, name='zipcode_search_api'),

    # 8. 管理者向けアカウント管理
    path('admin_dashboard/', views.admin_dashboard_view, name='admin'),
    path('admin_users/', views.admin_user_list_view, name='admin_user_list'),
    path('admin_users/<int:user_id>/', views.admin_user_details_view, name='admin_user_details'),
]