from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    # 1. トップ・メイン・マイページ
    path('', views.TopView.as_view(), name='top'),
    path('main/', views.MainView.as_view(), name='main'),
    path('mypage/', views.MypageView.as_view(), name='mypage'),

    # 2. ログイン・ログアウト
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # 3. アカウント新規登録
    path('register/', views.UserRegisterView.as_view(), name='user_register'),
    path('register/confirm/', views.UserRegisterConfirmView.as_view(), name='user_register_confirm'),
    path('register/done/', views.UserRegisterDoneView.as_view(), name='user_register_done'),

    # 4. アカウント変更
    path('update/', views.UserUpdateView.as_view(), name='user_update'),
    path('update/confirm/', views.UserUpdateConfirmView.as_view(), name='user_update_confirm'),
    path('update/done/', views.UserUpdateDoneView.as_view(), name='user_update_done'),

    # 5. アカウント削除
    path('archive/', views.UserArchiveView.as_view(), name='user_archive'),
    path('archive/done/', views.UserArchiveDoneView.as_view(), name='user_archive_done'),

    # 6. パスワード再設定
    path('password_reset/', views.PasswordResetLinkView.as_view(), name='password_reset_link'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset/<str:token>/', views.PasswordResetView.as_view(), name='password_reset'),

    # 7. 郵便番号検索API
    path('api/zipcode/', views.ZipcodeSearchApiView.as_view(), name='zipcode_search_api'),

    # 8. 管理者向けアカウント管理
    path('admin_dashboard/', views.AdminDashboardView.as_view(), name='admin'),
    path('admin_users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin_users/<int:user_id>/', views.AdminUserDetailsView.as_view(), name='admin_user_details'),
]