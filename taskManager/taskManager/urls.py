"""taskManager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from tasks import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('add_task', views.new),
    path('show_tasks', views.show_tasks),
    path('edit_task/<int:id>', views.edit_task),
    path('update_task/<int:id>', views.update_task),
    path('delete_task/<int:id>', views.kill_task),
    path('status/<int:id>', views.status),
    path('timestamp/<int:id>', views.timestamp),
    path('show_timestamps', views.show_timestamps),
    path('timestamp_search', views.timestamp_search),
    path('delete_timestamp/<int:id>', views.delete_timestamp),
    path('edit_timestamp/<int:id>', views.edit_timestamp),
    path('update_timestamp/<int:id>', views.update_timestamp),
	  path('show_time_dashboard', views.show_time_dashboard),
    path('show_task_dashboard', views.show_task_dashboard),
	  re_path(r'^$', views.index, name='index'),
]
