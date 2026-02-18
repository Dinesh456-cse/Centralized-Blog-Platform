# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].help_text = None
        self.fields["password1"].help_text = None
        self.fields["password2"].help_text = None


class UserLoginForm(AuthenticationForm):
    """
    Login form using username and password.
    """
    username = forms.CharField(label="Username")


class UserUpdateForm(forms.ModelForm):
    """
    Update basic user data (username, email).
    """
    class Meta:
        model = CustomUser
        fields = ("username", "email")


class ProfileUpdateForm(forms.ModelForm):
    """
    Update profile image.
    """
    class Meta:
        model = CustomUser
        fields = ("profile_image",)