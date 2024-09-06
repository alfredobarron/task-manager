from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from .models import Task
from .task import send_notification
import json


# Vista de inicio de sesión
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/login.html')

# Vista de cierre de sesión
def logout_view(request):
    logout(request)
    return redirect('login')

# Vista de registro de usuario
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})


@login_required
def index(request):
    return render(request, 'tasks/index.html')

@csrf_exempt
def task_list_create(request):
    if request.method == 'GET':
        tasks = Task.objects.all()
        paginator = Paginator(tasks, 10)  # Muestra 10 tareas por página
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        tasks_paginated = list(page_obj.object_list.values())
        return JsonResponse({
            'tasks': tasks_paginated,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'total_tasks': paginator.count
        })

    elif request.method == 'POST':
        data = json.loads(request.body)
        task = Task.objects.create(
            title=data['title'],
            description=data['description'],
            due_date=data['due_date'],
            email=data['email']
        )
        send_notification.delay('New Task Created', f'Task "{task.title}" was created', 'from@example.com', [task.email])
        return JsonResponse({'id': task.id, 'title': task.title}, status=201)


@csrf_exempt
def task_detail_update_delete(request, id):
    try:
        task = Task.objects.get(pk=id)
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)

    if request.method == 'PUT':
        data = json.loads(request.body)
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.save()
        send_notification.delay('Task Updated', f'Task "{task.title}" was updated', 'from@example.com', [task.email])
        return JsonResponse({'id': task.id, 'title': task.title})

    elif request.method == 'DELETE':
        task.delete()
        return JsonResponse({'message': 'Task deleted'}, status=204)
