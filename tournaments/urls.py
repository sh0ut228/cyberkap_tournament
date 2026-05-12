from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Team URLs
    path('teams/', views.teams_list, name='teams_list'),
    path('teams/create/', views.create_team, name='create_team'),
    path('teams/join/', views.join_team, name='join_team'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    
    # Tournament URLs
    path('tournaments/', views.tournaments_list, name='tournaments_list'),
    path('tournaments/create/', views.create_tournament, name='create_tournament'),
    path('tournaments/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('tournaments/<int:tournament_id>/register/', views.register_for_tournament, name='register_for_tournament'),
    
    # Admin URLs
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]