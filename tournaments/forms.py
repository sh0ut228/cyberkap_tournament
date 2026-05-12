from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Team, Tournament, TournamentRegistration

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    birth_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'birth_date', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.birth_date = self.cleaned_data['birth_date']
        user.role = 'player'
        if commit:
            user.save()
        return user

class CreateTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'tag', 'game', 'description', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean_name(self):
        name = self.cleaned_data['name']
        if Team.objects.filter(name=name).exists():
            raise forms.ValidationError('Команда с таким названием уже существует')
        return name

class CreateTournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'game', 'description', 'format', 'prize_pool', 
                  'start_date', 'end_date', 'registration_deadline', 
                  'min_players', 'max_teams', 'banner']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'registration_deadline': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_deadline = cleaned_data.get('registration_deadline')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('Дата начала не может быть позже даты окончания')
        
        if registration_deadline and start_date and registration_deadline > start_date:
            raise forms.ValidationError('Дедлайн регистрации должен быть раньше даты начала турнира')
        
        return cleaned_data

class JoinTeamForm(forms.Form):
    team_code = forms.CharField(max_length=100, label='Название команды')
    
    def clean_team_code(self):
        team_name = self.cleaned_data['team_code']
        try:
            team = Team.objects.get(name=team_name)
            return team
        except Team.DoesNotExist:
            raise forms.ValidationError('Команда не найдена')