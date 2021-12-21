from django.shortcuts import render, redirect
from tasks.forms import TaskForm, UpdateTaskForm, StatusForm, TimestampSearchForm, UpdateTsForm, DateFilter
from tasks.models import Task, Timestamp
from django.utils import timezone
from collections import defaultdict
from django.db.models import Sum
from datetime import timedelta, date, datetime
import pytz
import math

# Create your views here.
#When you access the main page (127.0.0.1/8000/) automatically redirect to show_tasks page
def index(request):
	return redirect("/show_tasks")
    
#add task page
def new(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return redirect('/show_tasks')
            except:
                pass
    else:
        form = TaskForm()
    return render(request,'add_task.html',{'form':form})

    
def show_tasks(request):
    tasks = Task.objects.all()
    return render(request, "show_tasks.html", {'tasks':tasks})

#show edit task page    
def edit_task(request, id):
    tasks = Task.objects.get(id=id)
    form = UpdateTaskForm(initial={'task_name':tasks.task_name, 'task_description':tasks.task_description, 'project':tasks.project})
    return render(request, "edit_task.html", {'tasks':tasks, 'form':form})

#take edit task input and actually update the database
def update_task(request, id):
    tasks = Task.objects.get(id=id)
    if request.method == "POST":
        form = UpdateTaskForm(request.POST, instance=tasks)
        if form.is_valid():
            try:
                form.save()
                return redirect('/show_tasks')
            except:
                pass
    else:
        form = UpdateTaskForm(initial={'task_name':tasks.task_name, 'task_description':tasks.task_description, 'project':tasks.project})   
    return render(request, "edit_task.html", {'tasks':tasks, 'form':form})

#delete task
def kill_task(request, id):
    task = Task.objects.get(id=id)
    task.delete()
    return redirect("/show_tasks")

#update taks status
def status(request, id):
    tasks = Task.objects.get(id=id)
    form = StatusForm(request.POST, instance=tasks)
    form.save()
    return redirect("/show_tasks")

#Create new timestamp for a task    
def timestamp(request, id):
    task = Task.objects.get(id=id)
    #If timer state is 'start timer' the task does not have an active timestamp so set begin_time and flip timer state
    if(task.timer_state == 'Start Timer'):
        task.begin_time = timezone.now()
        task.timer_state = "Stop Timer"
        task.save()
    #If timer state is 'stop timer', a timestamp has already been started so create a new timestamp object and flip timer state
    else:
        new_ts = Timestamp(task=task, begin_time=task.begin_time, end_time=timezone.now())
        task.timer_state = "Start Timer"
        task.save()
        new_ts.save()
    return redirect("/show_tasks")

#Task filter on list of timestamps    
def timestamp_search(request):
    form = TimestampSearchForm(request.POST)
    if form.is_valid():
        timestamps = Timestamp.objects.filter(task__task_name=form.cleaned_data['task_name']).order_by('begin_time')
        return render(request, "show_timestamps.html", {'timestamps':timestamps})
    return redirect("/show_timestamps")
    
def show_timestamps(request):
    timestamps = Timestamp.objects.all().order_by('begin_time')
    return render(request, "show_timestamps.html", {'timestamps':timestamps})

def delete_timestamp(request, id):
    ts = Timestamp.objects.get(id=id)
    # Attempts to retain a search. If the request came from show_timestamps it came from the full list of timestamps so return the full list
    if "show_timestamps" in request.META['HTTP_REFERER']:  
        ts.delete()
        return redirect("/show_timestamps")
    # otherwise, redo the search for a task and return the filtered list
    else:
        ts.delete()
        timestamps = Timestamp.objects.filter(task__task_name=ts.task.task_name).order_by('begin_time')
        return render(request, "show_timestamps.html", {'timestamps':timestamps})

#same process as edit_task
def edit_timestamp(request, id):
    timestamp=Timestamp.objects.get(id=id)
    form = UpdateTsForm()
    return render(request, 'edit_timestamp.html', {'timestamp':timestamp, 'form':form})
    
#Because edit, update is a 2 step process, cannot use the HTTP_REFERER trick to retain a search, so edit will always return the full list of timestamps
def update_timestamp(request, id):
    timestamp = Timestamp.objects.get(id=id)
    if request.method == 'POST':
        form = UpdateTsForm(request.POST, instance=timestamp)
        if form.is_valid() and form.cleaned_data['begin_time'] < form.cleaned_data['end_time']:
            try:
                form.save()
                return redirect("/show_timestamps")
            except:
                pass
    form = UpdateTsForm()
    return render(request, "edit_timestamp.html", {'form':form, 'timestamp':timestamp})

def show_time_dashboard(request):
    tasks = Task.objects.all()
    ts_total = {}
    ts_week = {}
    ts_month = {}
    if request.method == 'POST':
        #If a date is specified, extract the year, month, and the start of the week
        date_form = DateFilter(request.POST)
        if date_form.is_valid():
            year = date_form.cleaned_data['day'].year
            month = date_form.cleaned_data['day'].month
            week_start = date_form.cleaned_data['day'] - timedelta(days=date_form.cleaned_data['day'].weekday())
    #Otherwise use todays date
    else:
        date_form = DateFilter()
        year = date.today().year
        month = date.today().month
        week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    #Calculate the week and month start and end as a localized datetime. This makes calculations with the timestamp values easier as everything is the same type
    #Also fixes a bug where because datetimes are always stored in the database as UTC times, datetime.day would be off by 1 if the datetime is late at night or early in the morning because of time change
    week_start_time = pytz.timezone('US/Eastern').localize(datetime.combine(week_start, datetime.min.time()))
    week_end_time = pytz.timezone('US/Eastern').localize(datetime.combine(week_end, datetime.max.time()))
    month_start_time = pytz.timezone('US/Eastern').localize(datetime(year, month, 1, 0, 0))
    month_end_time = pytz.timezone('US/Eastern').localize(datetime((year+1 if month==12 else year), (1 if month==12 else month+1), 1, 0, 0))
    #Looks for projects for the filter by projects later
    projects = set()
    for task in tasks:
        timestamps = Timestamp.objects.filter(task__id=task.id)
        projects.add(task.project)
        #Total time for each task
        ts_total[task.id] = 0
        #Time spent on the task this week
        ts_week[task.id] = 0
        #Time spent on the task this month
        ts_month[task.id] = 0
        for timestamp in timestamps:
            ts_total[task.id] += timestamp.elapsed_time()
            #If the timestamp begins and ends withing the week, whole timestamp is added to weekly time
            if timestamp.begin_time >= week_start_time and timestamp.end_time <= week_end_time:
                ts_week[task.id] += timestamp.elapsed_time()
            #If timestamps starts before the week but ends within the week, only the time between the start of the week and the end of the timestamp is added
            if timestamp.begin_time < week_start_time and timestamp.end_time <= week_end_time and timestamp.end_time > week_start_time:
                ts_week[task.id] += math.floor((timestamp.end_time - week_start_time).total_seconds()/60)
            #If the timestamp starts during the week but ends after the week, only the time from the start of the timestamp to the end of the week is added
            if timestamp.begin_time <= week_end_time and timestamp.begin_time >= week_start_time and timestamp.end_time > week_end_time:
                ts_week[task.id] += math.floor((week_end_time - timestamp.begin_time).total_seconds()/60) + 1 #Need +1 because week_end_time is at 11:59 pm, need to add last minute
            #If the timestamp starts before the week and ends after the week, the whole week is added
            if timestamp.begin_time < week_start_time and timestamp.end_time > week_end_time:
                ts_week[task.id] += math.floor((week_end_time - week_start_time).total_seconds()/60) + 1
            #Same logic for month as for week
            if timestamp.begin_time >= month_start_time and timestamp.end_time <= month_end_time:
                ts_month[task.id] += timestamp.elapsed_time()
            if timestamp.begin_time < month_start_time and timestamp.end_time <= month_end_time and timestamp.end_time > month_start_time:
                ts_month[task.id] += math.floor((timestamp.end_time - month_start_time).total_seconds()/60)
            if timestamp.begin_time >= month_start_time and timestamp.end_time > month_end_time and timestamp.begin_time < month_end_time:
                ts_month[task.id] += math.floor((month_end_time - timestamp.begin_time).total_seconds()/60)
            if timestamp.begin_time < month_start_time and timestamp.end_time > month_end_time:
                ts_month[task.id] += math.floor((month_end_time - month_start_time).total_seconds()/60)
    
    p_total = {}
    p_week = {}
    p_month = {}
    #Does the exact same process as for tasks but loops through the different projects
    for project in projects:
        timestamps = Timestamp.objects.filter(task__project=project)
        p_total[project] = 0
        p_week[project] = 0
        p_month[project] = 0
        for timestamp in timestamps:
            p_total[project] += timestamp.elapsed_time()
            if timestamp.begin_time >= week_start_time and timestamp.end_time <= week_end_time:
                p_week[project] += timestamp.elapsed_time()
            if timestamp.begin_time < week_start_time and timestamp.end_time <= week_end_time and timestamp.end_time > week_start_time:
                p_week[project] += math.floor((timestamp.end_time - week_start_time).total_seconds()/60)
            if timestamp.begin_time <= week_end_time and timestamp.begin_time >= week_start_time and timestamp.end_time > week_end_time:
                p_week[project] += math.floor((week_end_time - timestamp.begin_time).total_seconds()/60) + 1
            if timestamp.begin_time < week_start_time and timestamp.end_time > week_end_time:
                p_week[project] += math.floor((week_end_time - week_start_time).total_seconds()/60) + 1
          
            if timestamp.begin_time >= month_start_time and timestamp.end_time <= month_end_time:
                p_month[project] += timestamp.elapsed_time()
            if timestamp.begin_time < month_start_time and timestamp.end_time <= month_end_time and timestamp.end_time > month_start_time:
                p_month[project] += math.floor((timestamp.end_time - month_start_time).total_seconds()/60)
            if timestamp.begin_time >= month_start_time and timestamp.end_time > month_end_time and timestamp.begin_time < month_end_time:
                p_month[project] += math.floor((month_end_time - timestamp.begin_time).total_seconds()/60)
            if timestamp.begin_time < month_start_time and timestamp.end_time > month_end_time:
                p_month[project] += math.floor((month_end_time - month_start_time).total_seconds()/60)
            
    return render(request, "show_time_dashboard.html", {
        'tasks':tasks, 
        'ts_total':ts_total, 
        'date_form':date_form, 
        'ts_week':ts_week, 
        'ts_month':ts_month, 
        'week_start':week_start,
        'month':datetime.strptime(str(month), "%m").strftime("%B"),
        'projects':projects,
        'p_total':p_total,
        'p_week':p_week,
        'p_month':p_month,
    })
  
def show_task_dashboard(request):
    tasks = Task.objects.all()
    ts_total = {}
    ts_week = {}
    ts_month = {}
    #Same date logic as in show_time_dasboard
    if request.method == 'POST':
        date_form = DateFilter(request.POST)
        if date_form.is_valid():
            year = date_form.cleaned_data['day'].year
            month = date_form.cleaned_data['day'].month
            week_start = date_form.cleaned_data['day'] - timedelta(days=date_form.cleaned_data['day'].weekday())
    else:
        date_form = DateFilter()
        year = date.today().year
        month = date.today().month
        week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    week_start_time = pytz.timezone('US/Eastern').localize(datetime.combine(week_start, datetime.min.time()))
    week_end_time = pytz.timezone('US/Eastern').localize(datetime.combine(week_end, datetime.max.time()))
    month_start_time = pytz.timezone('US/Eastern').localize(datetime(year, month, 1, 0, 0))
    month_end_time = pytz.timezone('US/Eastern').localize(datetime((year+1 if month==12 else year), (1 if month==12 else month+1), 1, 0, 0))
    ts_total_avg = {}
    ts_week_avg = {}
    ts_month_avg = {}
    ts_total_pct = {}
    ts_week_pct = {}
    ts_month_pct = {}
    #Counting total time spent for % of time spent value
    total_time = 0
    total_week_time = 0
    total_month_time = 0    
    for task in tasks:
        timestamps = Timestamp.objects.filter(task__id=task.id)
        ts_total[task.id] = 0
        ts_week[task.id] = 0
        ts_month[task.id] = 0
        #Counting total number of timestamps for a task for average timestamp duration
        ts_total_count = 0
        #Counting total timestamps for the week
        ts_week_count = 0
        #Counting total timestamps for the month
        ts_month_count = 0
        #All the same logic as show_time_dashboard but also updates timestamp counts and time counts
        for timestamp in timestamps:
            ts_total[task.id] += timestamp.elapsed_time()
            ts_total_count += 1
            total_time += timestamp.elapsed_time()
            if timestamp.begin_time >= week_start_time and timestamp.end_time <= week_end_time:
                ts_week[task.id] += timestamp.elapsed_time()
                ts_week_count += 1
                total_week_time += timestamp.elapsed_time()
            if timestamp.begin_time < week_start_time and timestamp.end_time <= week_end_time and timestamp.end_time > week_start_time:
                ts_week[task.id] += math.floor((timestamp.end_time - week_start_time).total_seconds()/60)
                ts_week_count += 1
                total_week_time += math.floor((timestamp.end_time - week_start_time).total_seconds()/60)
            if timestamp.begin_time <= week_end_time and timestamp.begin_time >= week_start_time and timestamp.end_time > week_end_time:
                ts_week[task.id] += math.floor((week_end_time - timestamp.begin_time).total_seconds()/60) + 1
                ts_week_count += 1
                total_month_time += math.floor((week_end_time - timestamp.begin_time).total_seconds()/60) + 1
            if timestamp.begin_time < week_start_time and timestamp.end_time > week_end_time:
                ts_week[task.id] += math.floor((week_end_time - week_start_time).total_seconds()/60) + 1
                ts_week_count += 1
                total_week_time += math.floor((week_end_time - week_start_time).total_seconds()/60) + 1
          
            if timestamp.begin_time >= month_start_time and timestamp.end_time <= month_end_time:
                ts_month[task.id] += timestamp.elapsed_time()
                ts_month_count += 1
                total_month_time += timestamp.elapsed_time()
            if timestamp.begin_time < month_start_time and timestamp.end_time <= month_end_time and timestamp.end_time > month_start_time:
                ts_month[task.id] += math.floor((timestamp.end_time - month_start_time).total_seconds()/60)
                ts_month_count += 1
                total_month_time += math.floor((timestamp.end_time - month_start_time).total_seconds()/60)
            if timestamp.begin_time >= month_start_time and timestamp.end_time > month_end_time and timestamp.begin_time < month_end_time:
                ts_month[task.id] += math.floor((month_end_time - timestamp.begin_time).total_seconds()/60)
                ts_month_count += 1
                total_month_time += math.floor((month_end_time - timestamp.begin_time).total_seconds()/60)
            if timestamp.begin_time < month_start_time and timestamp.end_time > month_end_time:
                ts_month[task.id] += math.floor((month_end_time - month_start_time).total_seconds()/60)
                ts_month_count += 1
                total_month_time += math.floor((month_end_time - month_start_time).total_seconds()/60)
      
        #Computing averages for timestamp length, if ts_XXXX_count == 0, there are no timestamps for that period so return 0
        ts_total_avg[task.id] =  round(ts_total[task.id] / ts_total_count, 1) if ts_total_count else 0
        ts_week_avg[task.id] = round(ts_week[task.id] / ts_week_count, 1) if ts_week_count else 0
        ts_month_avg[task.id] = round(ts_month[task.id] / ts_month_count, 1) if ts_month_count else 0
        
    
    #Computing percentage of time spent for on each task for each time period
    for task in tasks:
        ts_total_pct[task.id] = round((ts_total[task.id] / total_time)*100) if total_time else 0
        ts_week_pct[task.id] = round((ts_week[task.id] / total_week_time)*100) if total_week_time else 0
        ts_month_pct[task.id] = round((ts_month[task.id] / total_month_time)*100) if total_month_time else 0
        
    return render(request, "show_task_dashboard.html", {
        'ts_total_avg':ts_total_avg,
        'ts_week_avg':ts_week_avg,
        'ts_month_avg':ts_month_avg,
        'date_form':date_form,
        'week_start':week_start,
        'month':datetime.strptime(str(month), "%m").strftime("%B"),
        'tasks':tasks, 
        'ts_total_pct':ts_total_pct,
        'ts_week_pct':ts_week_pct,
        'ts_month_pct':ts_month_pct,
    })
        

