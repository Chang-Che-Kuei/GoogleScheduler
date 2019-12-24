from django.contrib import admin 
from django.contrib.auth.models import User 
from django.db import models 
from oauth2client.contrib.django_util.models import CredentialsField 
from datetime import datetime  
  
class CredentialsModel(models.Model): 
    id = models.ForeignKey(User, primary_key = True, on_delete = models.CASCADE) 
    credential = CredentialsField()
    task = models.CharField(max_length = 80, null = True) 
    email = models.CharField(max_length = 80, null = True)
    username = models.CharField(max_length = 80, null = True)
    
    #新增
    # nickname = models.CharField(max_length=30)
    user_image = models.ImageField(upload_to='media/image/',default="image/photo.png") 
  
  
class Event(models.Model):
    priority = models.IntegerField()
    event_id = models.CharField(max_length=120, null = True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.IntegerField()
    event_type = models.IntegerField()
    PreparingHours = models.IntegerField(default=0)
    deadline = models.DateTimeField()
#
