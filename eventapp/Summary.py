#!/usr/bin/env python3
from eventapp.models import *
import datetime
import dateutil.parser
import pytz
import numpy as np
import sys, random, string
from eventapp.ResourceManager import ResourceManager
class Summary:
    def __init__(self):
        #self.rm = ResourceManager(service)
        pass

    def GetUTCtimezone(self,date):
        d = datetime.datetime(date[0],date[1],date[2],date[3],date[4])
        #create Taipei timezone
        tw = pytz.timezone('Asia/Taipei')
        d = tw.localize(d)
        #change to utc time
        d = d.astimezone(pytz.utc).isoformat()
        d = d[:-6] + 'Z'
        return d

    def get_completion_rate(self, start, end):
        #start = self.GetUTCtimezone([2019, 12, 22, 0, 0])
        #start = self.rm.GetUTCtimezone([2019, 12, 22, 0, 0])
        #print(start, end)
        late = Event.objects.filter(start_time__gt=start).filter(end_time__lt=end).filter(status=0)
        #print(late)
        complete = Event.objects.filter(start_time__gt=start).filter(end_time__lt=end).filter(status=1)
        print(len(late), len(complete))
        #print(type(late[0].start_time), late[0].start_time)

        total = max(len(late) + len(complete), 1)

        late_big = 0
        late_small = 0
        complete_big = 0
        complete_small = 0
        if len(late) > 0:
            for i in range(len(late)):
                if late[i].event_type == 1:
                    late_big += 1
                else:
                    late_small += 1
            late_big /= len(late)
            late_small /= len(late)
        if len(complete) > 0:
            for i in range(len(complete)):
                if complete[i].event_type == 1:
                    complete_big += 1
                else:
                    complete_small += 1
            complete_big /= len(complete)
            complete_small /= len(complete)
        return len(late) / total, len(complete) / total, late_big, late_small, complete_big, complete_small

