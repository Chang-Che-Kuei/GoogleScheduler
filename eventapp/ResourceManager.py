#!/usr/bin/env python3
from eventapp.models import *
import datetime
import dateutil.parser
import pytz
import numpy as np
import sys, random, string
#from eventapp.ScheduleAlgorithm import ScheduleAlgorithm
'''
There are 6 keys will be saved in our databases
'priority': int (integer), default is -1
'id': a string and the length is 100, please call generate_string function to generate id for the event
'start_time': a datetime object, as same as events['start']['dateTime']
'end_time': a datetime object, as same as events['end']['dateTime']
'status': int (0 / 1), 0 for unfinished, 1 for finished event, default is 0
'event_type': int (0 / 1) 0 for the small events, 1 for the events which need preparation events, 2 for the preparation events, default is 0
'relational_id': a string, which contains the ids of related events
'''

class ResourceManager:
    def __init__(self, service):
        self.service = service

    def GetUTCtimezone(self,date):
        d = datetime.datetime(date[0],date[1],date[2],date[3],date[4])
        #create Taipei timezone
        tw = pytz.timezone('Asia/Taipei')
        d = tw.localize(d)
        #change to utc time
        d = d.astimezone(pytz.utc).isoformat()
        d = d[:-6] + 'Z'
        return d

    def generate_string(self):
        '''
        You can call this function to generate a valid event_id
        '''
        return ''.join(random.choice(string.ascii_lowercase[:-5] + string.digits) for _ in range(20))

    def get_eventType(self, Id):
        x = Event.objects.filter(event_id=Id)[0]
        return x.event_type
        

    def get_all_events(self, start, end=None):
        '''
        Arguments:
        start is the return value from GetUTCtimezone
        If end is specified, then the function will return the events in the timerange [start, end]
        Otherwise, this function will return any events from now

        Return:
        a list which contains multiple dictionaries. Each dictionaries is an event. The events are sorted by start time
        '''
        if end == None:
            print('start = ', start)
            events_result = self.service.events().list(calendarId='primary', timeMin=start, singleEvents=True, orderBy='startTime').execute()
        else:
            events_result = self.service.events().list(calendarId='primary', timeMin=start, timeMax=end, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        print(len(events))
        for i in range(len(events)):
            x = Event.objects.filter(event_id=events[i]['id'])[0]
            self.add_attribute(events[i], x)
        return events

    def get_calendar(self):
        return self.service.calendars().get(calendarId='primary').execute()

    def delete_event(self, eventId, flag=0):
        '''
        Argument:
        eventId of the deleted event
        
        This function will delete the event in google database only
        '''
        self.service.events().delete(calendarId='primary', eventId=eventId).execute()
        if flag == 1:
            Event.objects.filter(event_id=eventId).delete()

    def update_event(self, event):
        '''
        Argument:
        a dictionary of the updated event

        This function will save the updated information in our database and google database
        '''
        #print(event)
        x = Event.objects.filter(event_id=event['id'])[0]
        x.priority = event['priority']
        x.status = event['status']
        x.start_time = event['start']['dateTime']
        x.end_time = event['end']['dateTime']
        x.event_type = event['eventType']
        x.PreparingHours = event['PreparingHours']
        x.deadline = event['deadline']
        x.save()
        event = self.remove_attribute(event)
        self.service.events().patch(calendarId='primary', eventId=event['id'], body=event).execute()

    def insert_event(self, event):
        '''
        Arguments:
        event is a dictionary

        This function will create an event into our database and google database
        '''
        if 'id' not in event:
            event['id'] = self.generate_string()
        if 'priority' not in event:
            event['priority'] = -1
        if 'eventType' not in event:
            event['eventType'] = 0
        if 'status' not in event:
            event['status'] = 0
        if 'PreparingHours' not in event:
            event['PreparingHours'] = 0
        if 'deadline' not in event:
            event['deadline'] = event['end']['dateTime']
        #print('event = ', event)
        Event.objects.create(priority=event['priority'], event_id=event['id'],
                            start_time=event['start']['dateTime'],
                            end_time=event['end']['dateTime'], status=event['status'], event_type=event['eventType'], PreparingHours=event['PreparingHours'], deadline=event['deadline'])
        print(event)
        event = self.remove_attribute(event)
        self.service.events().insert(calendarId='primary', body=event).execute()

    def get_one_event(self, eventId):
        '''
        Arguments:
        eventId is a string

        Given an eventId, this function will return an event
        '''
        print(eventId) 
        events = self.service.events().get(calendarId='primary', eventId=eventId).execute()
        x = Event.objects.filter(event_id=eventId)[0]
        print(x.start_time, type(x.start_time))
        self.add_attribute(events, x)
        return events

    def get_head_event(self, name):
        events_result = self.service.events().list(calendarId='primary', singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        for i in range(len(events)):
            if name[:-12] == events[i]['summary']:
                x = Event.objects.filter(event_id=events[i]['id'])[0]
                self.add_attribute(events[i], x)
                return events[i]
        return None
    
    def get_preparation_event(self, eventId, start, end):
        '''
        Arguments:
        eventId is a string
        start is the return value of GetUTCtimezone

        Return:
        a list which contains multiple dictionary, each dictionary represents an event which is related to the eventId

        For example, if you give the eventId of 'testing', then it will return a list which contains the dictionaries of 'testing_Preparation'
        If you give the eventId of 'testing_Preparation', then it will return a list which contains the dictionaries of 'testing_Preparation' without including the event of the arguments
        '''
        # return list of dictionary
        ret = []
        event = self.service.events().get(calendarId='primary', eventId=eventId).execute()
        name = event['summary']
        print(name)
        events_result = self.service.events().list(calendarId='primary', timeMin=start, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        for i in range(len(events)):
            if '_Preparation' not in name:
                if name + '_Preparation' == events[i]['summary']:
                    x = Event.objects.filter(event_id=events[i]['id'])[0]
                    events[i] = self.add_attribute(events[i], x)
                    ret.append(events[i])
            elif '_Preparation' in name:
                if name == events[i]['summary'] or name[:-12] == events[i]['summary']:
                    x = Event.objects.filter(event_id=events[i]['id'])[0]
                    events[i] = self.add_attribute(events[i], x)
                    if events[i]['id'] != event['id']:
                        ret.append(events[i])
        return ret
   
    def add_attribute(self, event, x):
        event['priority'] = x.priority
        event['status'] = x.status
        event['eventType'] = x.event_type
        event['PreparingHours'] = x.PreparingHours
        event['deadline'] = x.deadline
        return event


    def remove_attribute(self, event):
        event.pop('priority')
        event.pop('status')
        event.pop('eventType')
        event.pop('PreparingHours')
        event.pop('deadline')
        return event
