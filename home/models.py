from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import F

# Create your models here.
class Question(models.Model):
    question_text = models.CharField(max_length=255)
    option_a = models.CharField(max_length=100)
    option_b = models.CharField(max_length=100)
    option_c = models.CharField(max_length=100)
    option_d = models.CharField(max_length=100)
    correct_option = models.CharField(max_length=1)
    difficulty = models.FloatField(default=1.0)  # Use FloatField for finer control
    topic =models.CharField(max_length=200, default="General")
    weight = models.FloatField(default=1.0)  # Weight for question importance/difficulty
    intrinsic_difficulty = models.FloatField(default=1.0) # Static difficulty of question

    def __str__(self):
        return self.question_text


class UserPerformance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    difficulty_score = models.FloatField(default=1.0)
    score = models.IntegerField(default=0)
    quizzes_taken = models.IntegerField(default=0)
    streak_count = models.IntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)

    def adjust_difficulty(self, quiz_results):
        num_questions = len(quiz_results)
        if num_questions == 0:
            return

        num_correct = sum(1 for result in quiz_results if result['is_correct'])
        total_time = sum(result['time_taken'] for result in quiz_results if result['time_taken'] is not None)

        accuracy_factor = num_correct / num_questions
        average_time_per_question = total_time / num_questions if num_questions > 0 and total_time is not None else 10

        difficulty_change = 0.0  # Initialize with a smaller change

        # Adjust based on accuracy with finer gradients
        if accuracy_factor > 0.9:
            difficulty_change += 0.03
        elif accuracy_factor > 0.8:
            difficulty_change += 0.02
        elif accuracy_factor > 0.7:
            difficulty_change += 0.01
        elif accuracy_factor < 0.3:
            difficulty_change -= 0.03
        elif accuracy_factor < 0.4:
            difficulty_change -= 0.02
        elif accuracy_factor < 0.5:
            difficulty_change -= 0.01

        # Adjust based on time with finer gradients and less impact
        if average_time_per_question < 7:
            difficulty_change += 0.015
        elif average_time_per_question < 9:
            difficulty_change += 0.01
        elif average_time_per_question > 16:
            difficulty_change -= 0.015
        elif average_time_per_question > 14:
            difficulty_change -= 0.01

        # Apply a smaller overall scaling factor to the change
        self.difficulty_score += difficulty_change * 0.5  # Reduce the impact of each quiz

        self.difficulty_score = max(0.5, min(self.difficulty_score, 3.0))
        self.save()

    def calculate_accuracy(self):
        if self.quizzes_taken > 0:
            total_possible_score = self.quizzes_taken * 5
            if total_possible_score > 0:
                return round((self.score / total_possible_score) * 100, 2)
        return 0

    def __str__(self):
        return f"{self.user.username} - Difficulty: {self.difficulty_score}"

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    topic =models.CharField(max_length=200, default='General')
    date_taken = models.DateTimeField(auto_now_add=True)
    questions = models.TextField(blank=True)  # Store question IDs
    difficulties = models.TextField(blank=True)  # Store difficulties for each question
    times_taken = models.TextField(blank=True) #Store time taken for each question

    def __str__(self):
        return f"{self.user.username} - {self.topic} - {self.date_taken.strftime('%Y-%m-%d')}"