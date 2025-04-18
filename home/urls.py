from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.user_profile, name='user_profile'),
    path('quiz/', views.take_quiz, name='take_quiz'),
    path('practice/', views.practice_quiz, name='practice_quiz'),
    path('history/', views.quiz_history, name='quiz_history'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('leaderboard/top-scores/', views.leaderboard_top_scores, name='leaderboard_top_scores'),
    path('leaderboard/most-quizzes/', views.leaderboard_most_quizzes, name='leaderboard_most_quizzes'),
    path('leaderboard/best-accuracy/', views.leaderboard_best_accuracy, name='leaderboard_best_accuracy'),
    path('submit/', views.submit_quiz, name='submit_quiz'),
    path('questions/', views.manage_questions, name='manage_questions'),
    path('questions/add/', views.add_question, name='add_question'),
    path('questions/edit/<int:question_id>/', views.edit_question, name='edit_question'),
    path('questions/delete/<int:question_id>/', views.delete_question, name='delete_question'),
    path('questions/bulk_delete/', views.bulk_delete_questions, name='bulk_delete_questions'),
    path('questions/upload_csv/', views.upload_questions_csv, name='upload_questions_csv'),
]
