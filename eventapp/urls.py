from django.conf.urls import url
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    url(r'^gmailAuthenticate', views.gmail_authenticate, name='gmail_authenticate'),
    url(r'^oauth2callback', views.auth_return),
    url(r'^$', views.home, name='home'),
    url(r'^home', views.home, name='home'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('forget_password/', views.forget_password, name='forget_password'),
    path('forget_password_page/', views.forget_password_page, name='forget_password_page'),
    # path('profile/', views.ProfileView.as_view(), name='profile'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('eventList/', views.eventList, name='eventList'),
    path('createEvent/', views.createEvent, name='createEvent'),
    path('profile/', views.profile, name='profile'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path('summary/', views.summary, name='summary'),
    path('setting/', views.setting, name='setting'),
    path('createSmallEvent/', views.createSmallEvent, name='createSmallEvent'),
    path('createBigEvent/', views.createBigEvent, name='createBigEvent'),
    # path('updateEventQuery/', views.updateEventQuery, name='updateEventQuery'),
    url('editEvent/$', views.editEvent, name='editEvent'),
    path('editEvent/small/<str:event_id>/', views.editSmallEvent, name='editSmallEvent'),
    path('editEvent/big/<str:event_id>/', views.editBigEvent, name='editBigEvent'),
    path('deleteSmallEvent/<str:event_id>/', views.deleteSmallEvent, name='deleteSmallEvent'),
    path('summary/showSummary.html', views.showsummary, name='showsummary'),
    path('deleteBigEvent/<str:event_id>/', views.deleteBigEvent, name='deleteBigEvent')
]
