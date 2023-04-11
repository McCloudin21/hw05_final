from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import (CreationForm,
                    PasswordChangeForm,
                    PasswordResetForm,
                    )


class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/signup'


class LogIn(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/login'


class PasswordReset(CreateView):
    form_class = PasswordResetForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/password_reset.html'


class PasswordChange(CreateView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/password_change'
