import csv
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import Question, UserPerformance, QuizAttempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import date, timedelta
from .forms import UserRegistrationForm, QuestionForm
from django.utils import timezone
from django.db.models import F
import random

def get_user_level(performance):
    if performance.difficulty_score < 1.5:
        return 'Beginner'
    elif performance.difficulty_score < 2.5:
        return 'Intermediate'
    else:
        return 'Advanced'

def home(request):
    return render(request, 'home.html')

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                User.objects.create_user(username=username, password=password)
                messages.success(request, "Registration successful! Please log in.")
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Registration failed: {e}")
                return render(request, 'register.html', {'form': form})
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
                return render(request, 'login.html', {'form': form})
        else:
            return render(request, 'login.html', {'form': form})
    else:
        form = UserRegistrationForm()
    return render(request, 'login.html', {'form': form})

def logout_user(request):
    logout(request)
    return redirect('home')

@login_required
def dashboard(request):
    performance, created = UserPerformance.objects.get_or_create(user=request.user)
    last_attempt = QuizAttempt.objects.filter(user=request.user).order_by('-date_taken').first()
    streak = performance.streak_count
    level = get_user_level(performance)

    # Calculate level progress percentage
    if level == 'Beginner':
        progress = (performance.difficulty_score / 1.5) * 100
    elif level == 'Intermediate':
        progress = ((performance.difficulty_score - 1.5) / (2.5 - 1.5)) * 100
    elif level == 'Advanced':
        progress = ((performance.difficulty_score - 2.5) / (3.0 - 2.5)) * 100 # Assuming max difficulty is 3.0
    else:
        progress = 0  # Default to 0 if level calculation fails

    level_progress_percent = min(100, max(0, round(progress))) # Ensure within 0-100

    context = {
        'user': request.user,
        'performance': performance,
        'last_attempt': last_attempt,
        'streak': streak,
        'level': level,
        'level_progress_percent': level_progress_percent,
    }
    return render(request, 'dashboard.html', context)

@login_required
def practice_quiz(request):
    if request.method == 'GET':
        topics = Question.objects.values_list('topic', flat=True).distinct()
        return render(request, 'practice_mode.html', {
            'topics': topics
        })

    selected_level = request.POST.get('level')
    if selected_level == 'Beginner':
        difficulties = [1.0]
    elif selected_level == 'Intermediate':
        difficulties = [1.0, 2.0]
    else:
        difficulties = [1.0, 2.0, 3.0]

    selected_topic = request.POST.get('topic')
    questions = Question.objects.filter(topic=selected_topic, difficulty__in=difficulties).order_by('?')[:5]
    topics = Question.objects.values_list('topic', flat=True).distinct()

    if not questions:
        messages.warning(request, "No practice questions found for that combination.")
        return redirect('practice_quiz')

    return render(request, 'quiz.html', {
        'questions': questions,
        'topic': selected_topic,
        'practice_mode': True
    })

@login_required
def take_quiz(request):
    performance, _ = UserPerformance.objects.get_or_create(user=request.user)

    # Determine user level and allowed difficulties
    if performance.quizzes_taken < 3:
        level = 'Beginner'
        allowed_difficulties = [1]
    elif performance.score / performance.quizzes_taken < 3:
        level = 'Intermediate'
        allowed_difficulties = [1, 2]
    else:
        level = 'Advanced'
        allowed_difficulties = [1, 2, 3]

    if request.method == 'GET':
        topics = Question.objects.filter(difficulty__in=allowed_difficulties)\
                                 .values_list('topic', flat=True).distinct()
        return render(request, 'select_topic.html', {
            'topics': topics,
            'level': level
        })

    # POST = user selected a topic to begin quiz
    selected_topic = request.POST.get('topic')
    difficulty_level = max(allowed_difficulties)

    questions = Question.objects.filter(topic=selected_topic, difficulty=difficulty_level).order_by('?')[:5]

    if not questions:
        messages.warning(request, f"No questions available for '{selected_topic}' at difficulty level {difficulty_level}.")
        return redirect('take_quiz')

    return render(request, 'quiz.html', {
        'questions': questions,
        'topic': selected_topic,
        'practice_mode': False,
        'level': level
    })


@login_required
def submit_quiz(request):
    perf, _ = UserPerformance.objects.get_or_create(user=request.user)

    today = date.today()
    yesterday = today - timedelta(days=1)

    if perf.last_practice_date == today:
        pass
    elif perf.last_practice_date == yesterday:
        perf.streak_count += 1
    else:
        perf.streak_count = 1

    perf.last_practice_date = today
    perf.save()

    if request.method == 'POST':
        score = 0
        total_questions = 0
        results = []
        topic = request.POST.get('topic', 'General')
        question_ids_str = []
        difficulty_levels_str = []
        times_taken_str = []  # To store time taken for each question as string

        answered_questions = {}
        times_taken_dict = {}
        for key, value in request.POST.items():
            if key.startswith('question_'):
                qid = int(key.split('_')[1])
                answered_questions[qid] = value
            elif key.startswith('time_'):
                qid = int(key.split('_')[1])
                try:
                    times_taken_dict[qid] = int(value)
                except ValueError:
                    times_taken_dict[qid] = None

        questions = Question.objects.filter(id__in=answered_questions.keys())
        question_dict = {q.id: q for q in questions}

        quiz_results_for_difficulty = []

        for qid_int, selected_answer in answered_questions.items():
            question = question_dict.get(qid_int)
            time_taken = times_taken_dict.get(qid_int)

            if question:
                total_questions += 1
                is_correct = question.correct_option == selected_answer
                if is_correct:
                    score += 1
                results.append({
                    'question': question,
                    'selected': selected_answer,
                    'is_correct': is_correct,
                    'time_taken': time_taken
                })
                question_ids_str.append(str(question.id))
                difficulty_levels_str.append(str(question.difficulty))
                times_taken_str.append(str(time_taken) if time_taken is not None else '')
                quiz_results_for_difficulty.append({'is_correct': is_correct, 'time_taken': time_taken})

        try:
            UserPerformance.objects.filter(user=request.user).update(
                score=F('score') + score,
                quizzes_taken=F('quizzes_taken') + 1
            )
            perf.refresh_from_db()
            perf.adjust_difficulty(quiz_results_for_difficulty)
        except Exception as e:
            messages.error(request, f"Error updating performance: {e}")

        if request.POST.get('practice_mode') == 'true':
            messages.info(request, "Practice attempt not recorded.")
            return render(request, 'quiz_result.html', {
                'score': score,
                'total': total_questions,
                'practice_mode': True,
                'topic': topic,
                'results': results
            })

        QuizAttempt.objects.create(
            user=request.user,
            score=score,
            total_questions=total_questions,
            topic=topic,
            questions=','.join(question_ids_str),
            difficulties=','.join(difficulty_levels_str),
            times_taken=','.join(times_taken_str)
        )

        return render(request, 'results.html', {
            'score': score,
            'results': results
        })

    return JsonResponse({'error': 'Invalid request'})

@user_passes_test(lambda u: u.is_superuser)
def add_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save()
            messages.success(request, "Question added successfully.")
            return redirect('manage_questions')
        else:
            messages.error(request, "There was an error adding the question.")
    else:
        form = QuestionForm()
    return render(request, 'add_question.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def edit_question(request, question_id):
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        messages.error(request, "Question not found.")
        return redirect('manage_questions')

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, "Question updated successfully.")
            return redirect('manage_questions')
        else:
            messages.error(request, "There was an error updating the question.")
    else:
        form = QuestionForm(instance=question)
    return render(request, 'edit_question.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def manage_questions(request):
    questions = Question.objects.all()
    topic_filter = request.GET.get('topic')
    difficulty_filter = request.GET.get('difficulty')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'id')

    if topic_filter:
        questions = questions.filter(topic=topic_filter)
    if difficulty_filter:
        questions = questions.filter(difficulty=difficulty_filter)
    if search_query:
        questions = questions.filter(question_text__icontains=search_query)
    if sort_by in ['question_text', 'topic', 'difficulty']:
        questions = questions.order_by(sort_by)

    topics = Question.objects.values_list('topic', flat=True).distinct()
    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'questions': page_obj,
        'topics': topics,
        'selected_topic': topic_filter,
        'selected_difficulty': difficulty_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'page_obj': page_obj
    }
    return render(request, 'manage_questions.html', context)

@user_passes_test(lambda u: u.is_superuser)
def delete_question(request, question_id):
    try:
        question = Question.objects.get(id=question_id)
        question.delete()
        messages.success(request, "Question deleted successfully.")
    except Question.DoesNotExist:
        messages.warning(request, "The question you're trying to delete doesn't exist.")
    except Exception as e:
        messages.error(request, f"Error deleting question: {e}")
    return redirect('manage_questions')

@user_passes_test(lambda u: u.is_superuser)
def bulk_delete_questions(request):
    if request.method == 'POST':
        ids = request.POST.getlist('question_ids')
        if ids:
            try:
                deleted_count, _ = Question.objects.filter(id__in=ids).delete()
                messages.success(request, f"Deleted {deleted_count} question(s) successfully.")
            except Exception as e:
                messages.error(request, f"Error deleting questions: {e}")
        else:
            messages.warning(request, "No questions selected for deletion.")
    return redirect('manage_questions')

@user_passes_test(lambda u: u.is_superuser)
def upload_questions_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        file = request.FILES['csv_file']
        file_path = default_storage.save('tmp/questions.csv', file)

        added_count = 0
        skipped_questions = []

        try:
            with open(default_storage.path(file_path), 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        difficulty = float(row.get('difficulty', 1.0))
                        weight = float(row.get('weight', 1.0))
                        intrinsic_difficulty = float(row.get('intrinsic_difficulty', 1.0))
                    except ValueError:
                        messages.error(request, f"Invalid numeric value in CSV for question: {row.get('question_text', 'N/A')}. Skipping.")
                        continue

                    if Question.objects.filter(question_text=row['question_text']).exists():
                        skipped_questions.append(row['question_text'])
                        continue

                    Question.objects.create(
                        question_text=row['question_text'],
                        option_a=row['option_a'],
                        option_b=row['option_b'],
                        option_c=row['option_c'],
                        option_d=row['option_d'],
                        correct_option=row['correct_option'],
                        difficulty=difficulty,
                        topic=row.get('topic', 'General'),
                        weight=weight,
                        intrinsic_difficulty=intrinsic_difficulty
                    )
                    added_count += 1

            if skipped_questions:
                skipped_detail = "Skipped questions due to duplicates:\n" + "\n".join(skipped_questions)
                messages.warning(request, skipped_detail)

            messages.success(request, f"Upload complete! {added_count} questions added, {len(skipped_questions)} skipped.")
        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")
        finally:
            default_storage.delete(file_path)

        return redirect('manage_questions')

    return render(request, 'upload_csv.html')

@login_required
def user_profile(request):
    performance, _ = UserPerformance.objects.get_or_create(user=request.user)
    accuracy = performance.calculate_accuracy()
    return render(request, 'user_profile.html', {'performance': performance, 'accuracy': accuracy})

@login_required
def quiz_history(request):
    topic_filter = request.GET.get('topic')
    history = QuizAttempt.objects.filter(user=request.user)

    if topic_filter:
        history = history.filter(topic=topic_filter)

    topics = QuizAttempt.objects.filter(user=request.user).values_list('topic', flat=True).distinct()
    recent = history.order_by('-date_taken').first()
    recent_topic = recent.topic if recent else None

    paginator = Paginator(history, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'quiz_history.html', {
        'history': page_obj,
        'topics': topics,
        'selected_topic': topic_filter,
        'recent_topic': recent_topic,
        'page_obj': page_obj
    })

@login_required
def leaderboard(request):
    return render(request, 'leaderboard.html')

def calculate_accuracy(user_performance):
    if user_performance.quizzes_taken > 0:
        # Assuming each quiz has 5 questions on average for this calculation
        return round((user_performance.score / (user_performance.quizzes_taken * 5)) * 100, 2)
    return 0

@login_required
def leaderboard_top_scores(request):
    top_users = UserPerformance.objects.select_related('user').order_by('-score')[:10]
    return render(request, 'leaderboard_top_scores.html', {'top_users': top_users})

@login_required
def leaderboard_most_quizzes(request):
    users = UserPerformance.objects.select_related('user').order_by('-quizzes_taken')[:10]
    return render(request, 'leaderboard_most_quizzes.html', {'top_users': users})

@login_required
def leaderboard_best_accuracy(request):
    users_performance = UserPerformance.objects.select_related('user').all()
    top_users = sorted([
        {'user': up.user, 'accuracy': calculate_accuracy(up)}
        for up in users_performance if up.quizzes_taken > 0
    ], key=lambda x: x['accuracy'], reverse=True)[:10]
    return render(request, 'leaderboard_best_accuracy.html', {'top_users': top_users})