from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from .models import CustomUser, Team, TeamMember, Tournament, TournamentRegistration, Winner
from .forms import RegisterForm, CreateTeamForm, CreateTournamentForm, JoinTeamForm
from .decorators import admin_required, captain_required
from datetime import date

def index(request):
    tournaments = Tournament.objects.filter(status='registration')[:4]
    winners = Winner.objects.select_related('tournament', 'team').order_by('-year', 'place')[:6]
    return render(request, 'tournaments/index.html', {
        'tournaments': tournaments,
        'winners': winners
    })

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'tournaments/login.html')

def user_register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'tournaments/register.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('index')

@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}
    
    if user.role == 'admin':
        context['total_tournaments'] = Tournament.objects.count()
        context['active_tournaments'] = Tournament.objects.filter(status='ongoing').count()
        context['total_teams'] = Team.objects.count()
        context['total_users'] = CustomUser.objects.count()
        context['recent_tournaments'] = Tournament.objects.order_by('-created_at')[:5]
        
    elif user.role == 'captain':
        try:
            team = Team.objects.get(captain=user)
            context['team'] = team
            context['team_members'] = team.get_members()
            context['pending_registrations'] = TournamentRegistration.objects.filter(
                team=team, status='pending'
            ).select_related('tournament')
            context['active_registrations'] = TournamentRegistration.objects.filter(
                team=team, status='approved'
            ).select_related('tournament')
        except Team.DoesNotExist:
            context['no_team'] = True
            
    elif user.role == 'player':
        try:
            team_member = TeamMember.objects.get(player=user)
            context['team'] = team_member.team
        except TeamMember.DoesNotExist:
            context['no_team'] = True
    
    return render(request, 'tournaments/dashboard.html', context)

@login_required
@captain_required
def create_team(request):
    if request.user.role == 'captain' and hasattr(request.user, 'captain_team'):
        messages.warning(request, 'Вы уже являетесь капитаном команды')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CreateTeamForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.captain = request.user
            team.save()
            
            # Обновляем роль пользователя на captain
            request.user.role = 'captain'
            request.user.save()
            
            messages.success(request, f'Команда "{team.name}" успешно создана!')
            return redirect('dashboard')
    else:
        form = CreateTeamForm()
    
    return render(request, 'tournaments/create_team.html', {'form': form})

@login_required
def join_team(request):
    if request.user.role == 'captain':
        messages.warning(request, 'Капитан не может присоединиться к команде')
        return redirect('dashboard')
    
    if request.user.team_member:
        messages.warning(request, 'Вы уже состоите в команде')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = JoinTeamForm(request.POST)
        if form.is_valid():
            team = form.cleaned_data['team_code']
            
            # Проверяем количество игроков в команде
            if team.get_member_count() >= 5:
                messages.error(request, 'В команде уже максимальное количество игроков (5)')
                return redirect('join_team')
            
            TeamMember.objects.create(team=team, player=request.user)
            messages.success(request, f'Вы успешно присоединились к команде "{team.name}"!')
            return redirect('dashboard')
    else:
        form = JoinTeamForm()
    
    teams = Team.objects.annotate(member_count=models.Count('members'))
    return render(request, 'tournaments/join_team.html', {'form': form, 'teams': teams})

@login_required
@admin_required
def admin_panel(request):
    tournaments = Tournament.objects.all().order_by('-created_at')
    teams = Team.objects.all()
    users = CustomUser.objects.all()
    registrations = TournamentRegistration.objects.select_related('tournament', 'team').all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve_registration':
            reg_id = request.POST.get('registration_id')
            registration = get_object_or_404(TournamentRegistration, id=reg_id)
            registration.status = 'approved'
            registration.save()
            messages.success(request, 'Заявка одобрена')
            
        elif action == 'reject_registration':
            reg_id = request.POST.get('registration_id')
            registration = get_object_or_404(TournamentRegistration, id=reg_id)
            registration.status = 'rejected'
            registration.save()
            messages.warning(request, 'Заявка отклонена')
            
        elif action == 'update_tournament_status':
            tournament_id = request.POST.get('tournament_id')
            new_status = request.POST.get('status')
            tournament = get_object_or_404(Tournament, id=tournament_id)
            tournament.status = new_status
            tournament.save()
            messages.success(request, f'Статус турнира обновлён')
    
    return render(request, 'tournaments/admin_panel.html', {
        'tournaments': tournaments,
        'teams': teams,
        'users': users,
        'registrations': registrations
    })

@login_required
@admin_required
def create_tournament(request):
    if request.method == 'POST':
        form = CreateTournamentForm(request.POST, request.FILES)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.created_by = request.user
            tournament.save()
            messages.success(request, f'Турнир "{tournament.name}" успешно создан!')
            return redirect('admin_panel')
    else:
        form = CreateTournamentForm()
    
    return render(request, 'tournaments/create_tournament.html', {'form': form})

def tournaments_list(request):
    tournaments = Tournament.objects.all().order_by('-start_date')
    status_filter = request.GET.get('status')
    
    if status_filter:
        tournaments = tournaments.filter(status=status_filter)
    
    return render(request, 'tournaments/tournaments_list.html', {'tournaments': tournaments})

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    registered_teams = tournament.registrations.filter(status='approved').select_related('team')
    can_register = False
    
    if request.user.is_authenticated:
        user_team = None
        if request.user.role == 'captain':
            try:
                user_team = Team.objects.get(captain=request.user)
            except Team.DoesNotExist:
                pass
        elif request.user.role == 'player':
            try:
                user_team = request.user.team_member.team
            except:
                pass
        
        if user_team:
            already_registered = TournamentRegistration.objects.filter(
                tournament=tournament, team=user_team
            ).exists()
            can_register = tournament.can_register() and not already_registered
    
    return render(request, 'tournaments/tournament_detail.html', {
        'tournament': tournament,
        'registered_teams': registered_teams,
        'can_register': can_register
    })

@login_required
def register_for_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Проверяем, есть ли у пользователя команда
    user_team = None
    if request.user.role == 'captain':
        try:
            user_team = Team.objects.get(captain=request.user)
        except Team.DoesNotExist:
            messages.error(request, 'Вы должны создать команду перед регистрацией')
            return redirect('create_team')
    elif request.user.role == 'player':
        try:
            user_team = request.user.team_member.team
        except:
            messages.error(request, 'Вы должны присоединиться к команде перед регистрацией')
            return redirect('join_team')
    else:
        messages.error(request, 'Только капитаны и игроки могут регистрироваться на турниры')
        return redirect('dashboard')
    
    # Проверяем, можно ли зарегистрироваться
    if not tournament.can_register():
        messages.error(request, 'Регистрация на этот турнир уже закрыта')
        return redirect('tournament_detail', tournament_id=tournament_id)
    
    # Проверяем, достаточно ли игроков в команде
    if user_team.get_member_count() < tournament.min_players - 1:  # -1 because captain is not in TeamMember
        messages.error(request, f'В вашей команде недостаточно игроков. Нужно минимум {tournament.min_players} игроков')
        return redirect('dashboard')
    
    # Проверяем, не зарегистрирована ли уже команда
    if TournamentRegistration.objects.filter(tournament=tournament, team=user_team).exists():
        messages.warning(request, 'Ваша команда уже зарегистрирована на этот турнир')
        return redirect('tournament_detail', tournament_id=tournament_id)
    
    # Создаём заявку
    TournamentRegistration.objects.create(
        tournament=tournament,
        team=user_team,
        status='pending'
    )
    
    messages.success(request, f'Команда "{user_team.name}" успешно зарегистрирована на турнир "{tournament.name}"!')
    return redirect('tournament_detail', tournament_id=tournament_id)

def teams_list(request):
    teams = Team.objects.filter(is_active=True).annotate(member_count=models.Count('members'))
    return render(request, 'tournaments/teams_list.html', {'teams': teams})

def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    members = team.get_members()
    tournaments = team.tournament_registrations.filter(status='approved').select_related('tournament')
    
    return render(request, 'tournaments/team_detail.html', {
        'team': team,
        'members': members,
        'tournaments': tournaments
    })