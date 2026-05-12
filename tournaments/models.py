from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('player', 'Игрок'),
        ('captain', 'Капитан'),
        ('admin', 'Администратор'),
    ]
    
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='player')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', null=True, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_captain(self):
        return self.role == 'captain'
    
    def get_team(self):
        if self.role == 'captain':
            try:
                return Team.objects.get(captain=self)
            except Team.DoesNotExist:
                return None
        elif self.role == 'player':
            try:
                return TeamMember.objects.get(player=self).team
            except TeamMember.DoesNotExist:
                return None
        return None

class Team(models.Model):
    GAME_CHOICES = [
        ('CS2', 'Counter-Strike 2'),
        ('DOTA2', 'Dota 2'),
        ('VALORANT', 'Valorant'),
    ]
    
    name = models.CharField('Название команды', max_length=100, unique=True)
    captain = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='captain_team')
    game = models.CharField('Игра', max_length=20, choices=GAME_CHOICES, default='CS2')
    tag = models.CharField('Тег команды', max_length=10, blank=True)
    description = models.TextField('Описание', blank=True)
    logo = models.ImageField('Логотип', upload_to='teams/', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_active = models.BooleanField('Активна', default=True)
    
    def __str__(self):
        return self.name
    
    def get_members(self):
        return TeamMember.objects.filter(team=self).select_related('player')
    
    def get_member_count(self):
        return self.get_members().count()
    
    def can_join_tournament(self, tournament):
        return self.get_member_count() >= tournament.min_players

class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    player = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='team_member')
    joined_at = models.DateTimeField('Дата вступления', auto_now_add=True)
    
    class Meta:
        unique_together = ['team', 'player']
    
    def __str__(self):
        return f"{self.player.username} - {self.team.name}"

class Tournament(models.Model):
    STATUS_CHOICES = [
        ('registration', 'Регистрация открыта'),
        ('ongoing', 'Идёт турнир'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    ]
    
    name = models.CharField('Название турнира', max_length=200)
    game = models.CharField('Игра', max_length=20, choices=Team.GAME_CHOICES)
    description = models.TextField('Описание')
    format = models.CharField('Формат', max_length=100, default='5x5')
    prize_pool = models.DecimalField('Призовой фонд', max_digits=12, decimal_places=2, default=0)
    
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    registration_deadline = models.DateField('Дедлайн регистрации')
    
    min_players = models.IntegerField('Минимум игроков', default=5)
    max_teams = models.IntegerField('Максимум команд', default=16)
    
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='registration')
    banner = models.ImageField('Баннер', upload_to='tournaments/', null=True, blank=True)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_tournaments')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def get_registered_teams_count(self):
        return self.registrations.filter(status='approved').count()
    
    def is_registration_open(self):
        return self.status == 'registration' and date.today() <= self.registration_deadline
    
    def can_register(self):
        return self.is_registration_open() and self.get_registered_teams_count() < self.max_teams

class TournamentRegistration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='registrations')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_registrations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tournament', 'team']
    
    def __str__(self):
        return f"{self.team.name} - {self.tournament.name}"

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team1')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team2')
    team1_score = models.IntegerField(default=0)
    team2_score = models.IntegerField(default=0)
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    match_date = models.DateTimeField()
    is_played = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.team1.name} vs {self.team2.name}"

class Winner(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='winners')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    place = models.IntegerField('Место', validators=[MinValueValidator(1), MaxValueValidator(3)])
    prize = models.DecimalField('Приз', max_digits=12, decimal_places=2, default=0)
    year = models.IntegerField('Год')
    
    class Meta:
        unique_together = ['tournament', 'place']
    
    def __str__(self):
        return f"{self.tournament.name} - {self.place} место: {self.team.name}"