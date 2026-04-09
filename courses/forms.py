from django import forms
from .models import (
    Course, Lesson, Quiz, Question, Assignment,
    Submission, CourseReview, Discussion, Reply
)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'short_description', 'thumbnail',
            'category', 'level', 'language', 'is_free', 'price',
            'discount_price', 'requirements', 'what_you_learn',
            'is_published', 'is_featured'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kurs nomi'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "O'zbek"}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'what_you_learn': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LessonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow auto-ordering when teacher doesn't set it manually.
        if 'order' in self.fields:
            self.fields['order'].required = False

    class Meta:
        model = Lesson
        fields = [
            'title', 'description', 'content', 'lesson_type',
            'video_url', 'video_file', 'attachment', 'duration',
            'order', 'is_free', 'is_published', 'xp_reward'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'lesson_type': forms.Select(attrs={'class': 'form-select'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'xp_reward': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'time_limit', 'passing_score',
            'max_attempts', 'shuffle_questions', 'show_correct_answers',
            'xp_reward', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'xp_reward': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'image', 'points', 'order']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'instructions', 'max_score', 'due_days', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'due_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['content', 'file']
        widgets = {
            'content': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Javobingizni yozing...'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [(i, f'{i} yulduz') for i in range(1, 6)]

    rating = forms.ChoiceField(choices=RATING_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = CourseReview
        fields = ['rating', 'title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sharh sarlavhasi'}),
            'content': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Fikringizni yozing...'}),
        }


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mavzu sarlavhasi'}),
            'content': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Savolingizni yozing...'}),
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Javob yozing...'}),
        }
