from django import forms
from tasks.models import Task, Timestamp

#Override dateinput and datetimeinput so that django can read the html date and datetime selectors
class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'
    
class DateInput(forms.DateInput):
    input_type = 'date'

#Add new task
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["task_name", "task_description", "project", "status"]
        
class UpdateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["task_name", "task_description", "project"]
        
class StatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status"]

#Task filter on list of timestamps        
class TimestampSearchForm(forms.Form):
    task_name = forms.CharField(label="id_task_name", max_length=100)

#Update Timestamp Form
class UpdateTsForm(forms.ModelForm):
    class Meta:
        model = Timestamp
        fields = ["begin_time", "end_time"]
        widgets = {'begin_time' : DateTimeInput(), 'end_time' : DateTimeInput()}   
        
#For week / month selector on dashboards      
class DateFilter(forms.Form):
    day = forms.DateField(label="date_filter", widget=DateInput())
