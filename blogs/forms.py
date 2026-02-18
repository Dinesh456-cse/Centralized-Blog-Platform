# blogs/forms.py
from django import forms
from .models import Blog


class BlogForm(forms.ModelForm):

    class Meta:
        model = Blog
        fields = [
            "title",
            "content",
            "category",
            "status",
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter blog title'
            }),
            'content': forms.Textarea(attrs={
                'rows': 15,
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 👤 Normal Users - status is NOT required, will be set by view
        if self.user and not self.user.is_staff:
            self.fields["status"].required = False
            self.fields["status"].initial = "draft"
            self.fields["status"].widget = forms.HiddenInput()

        # 👨‍💼 Admin Users - show status dropdown with all options
        elif self.user and self.user.is_staff:
            self.fields["status"].choices = [
                ("draft", "📝 Draft"),
                ("pending", "⏳ Pending Review"),
                ("published", "✅ Published"),
                ("rejected", "❌ Rejected"),
            ]

    def clean_status(self):
        """Ensure status has a valid value even if not submitted"""
        status = self.cleaned_data.get('status')
        
        if self.user and not self.user.is_staff:
            if not status or status == '':
                return 'draft'
        
        return status if status else 'draft'