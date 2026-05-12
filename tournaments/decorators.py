from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login')
        if request.user.role != 'admin':
            messages.error(request, 'Доступ запрещён. Требуются права администратора')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def captain_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login')
        if request.user.role not in ['captain', 'admin']:
            messages.error(request, 'Доступ запрещён. Требуются права капитана')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper