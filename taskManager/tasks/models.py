from django.db import models
import math

# Create your models here.
STATUSES = (
    ('in progress', 'In Progress'),
    ('completed', 'Complete'),
)

TIMER_STATE = (
    ('Start Timer', 'start timer'),
    ('Stop Timer', 'stop timer'),
)

class Timestamp(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, null=True)
    begin_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField()
    
    def elapsed_time(self):
        return math.floor(((self.end_time - self.begin_time).total_seconds()/60))
    class Meta:
        db_table = "timestamps"

class Task(models.Model):
    task_name = models.CharField(max_length=100)
    task_description = models.TextField()
    timer_state = models.CharField(max_length=11, choices=TIMER_STATE, default='Start Timer') #Used to determine if the task should be tracking time to create a timestamp
    begin_time = models.DateTimeField(blank=True, null=True) #Needed to record start time of timestamps. 
    project = models.CharField(max_length=100)
    status = models.CharField(max_length=11, choices=STATUSES, default='in progress')
    class Meta:
        db_table = "tasks"
