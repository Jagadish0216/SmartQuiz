from django import forms

class UserRegistrationForm(forms.Form):
     username = forms.CharField(
         label="Username",
         max_length=150,
         widget=forms.TextInput(attrs={'class': 'form-control'})
     )
     password = forms.CharField(
         label="Password",
         widget=forms.PasswordInput(attrs={'class': 'form-control'})
     )

class QuestionForm(forms.Form):
     question_text = forms.CharField(
         label="Question",
         widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
     )
     option_a = forms.CharField(label="Option A", widget=forms.TextInput(attrs={'class': 'form-control'}))
     option_b = forms.CharField(label="Option B", widget=forms.TextInput(attrs={'class': 'form-control'}))
     option_c = forms.CharField(label="Option C", widget=forms.TextInput(attrs={'class': 'form-control'}))
     option_d = forms.CharField(label="Option D", widget=forms.TextInput(attrs={'class': 'form-control'}))
     correct_option = forms.ChoiceField(
         label="Correct Option",
         choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
         widget=forms.Select(attrs={'class': 'form-control'})
     )
     difficulty = forms.IntegerField(
         label="Difficulty",
         widget=forms.NumberInput(attrs={'class': 'form-control'})
     )
     topic = forms.CharField(label="Topic", widget=forms.TextInput(attrs={'class': 'form-control'}))