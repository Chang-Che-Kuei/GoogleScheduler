import httplib2

from django.contrib.auth.forms import UserCreationForm
from googleapiclient.discovery import build
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from .models import CredentialsModel
from eventScheduler import settings
from oauth2client.contrib import xsrfutil
from oauth2client.client import flow_from_clientsecrets
from oauth2client.contrib.django_util.storage import DjangoORMStorage
from django.shortcuts import render, redirect, reverse
from django.views import View
from httplib2 import Http
import datetime
import pytz
import pdb
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
import smtplib
import secrets
import dateutil
from eventapp.User import User
from eventapp.ScheduleAlgorithm import ScheduleAlgorithm
from eventapp.ResourceManager import ResourceManager
from eventapp.Summary import Summary
from eventapp.Preference import Preference
SCOPE = 'https://www.googleapis.com/auth/calendar'
maxResultsNum=4
eventName_key = 'eventName'
eventType_key = 'eventType'
startTime_key = 'startTime'
endTime_key = 'endTime'
start_dateTime_key = 'start_dateTime'
end_dateTime_key = 'end_dateTime'
today_eventList = []

def home(request):
    print('***', 'views.home', '***')
    print('***', 'request.user:', request.user, '***')
    status = True
    events = {}
    if not request.user.is_authenticated:
        return redirect(reverse('register'))

    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()

    nickname = request.user.username

    if len(CredentialsModel.objects.filter(id = request.user)) > 0 :
        #print("CerdentialsModel :", CredentialsModel.objects.filter(id = request.user)[0].task)
        nickname = CredentialsModel.objects.filter(id = request.user)[0].task
        img = CredentialsModel.objects.filter(id = request.user)[0].user_image

    try:
        # access_token = credential.access_token
        # resp, cont = Http().request(SCOPE,
        #                             headers={'Host': 'www.googleapis.com',
        #                                     'Authorization': access_token})
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        service = build('calendar', 'v3', credentials=credential)
        rm = ResourceManager(service)
        email = service.calendars().get(calendarId='primary').execute()

        return render(request, 'index.html', {'user': nickname, 'img': img , 'status': status, 'events': events, 'email': email['summary']})


    except Exception as e:
        status = False
        print('e = ', e)
        #print('Not Found')
        return HttpResponseRedirect("/gmailAuthenticate/")
        # return render(request, 'index.html', {'user': nickname, 'status': status, 'events': events })

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html', { 'form': UserCreationForm() })

    def post(self, request):
        form = UserCreationForm(request.POST)
        print('***', 'get form', '***')
        if form.is_valid():
            print('***', 'form.is_valid', '***')
            user = form.save()
            return redirect(reverse('login'))
        else:
            print('***', 'form.is_NOT_valid', '***')

        return render(request, 'register.html', { 'form': form })


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html', { 'form':  AuthenticationForm })

    # low level but, using AuthenticationForm.clean for authentication
    def post(self, request):
        print('***', 'views.login', '***')
        print('***', 'username:', request.POST["username"], '***')
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            print("from.is_valid()")
            try:
                form.clean()
            except ValidationError:
                return render( request,'login.html',{ 'form': form, 'invalid_creds': True } )

            login(request, form.get_user())
            return redirect(reverse('home'))
        message = "Your username or password is incorrect"
        return render(request, 'login.html', { 'form': form , 'message': message})

def forget_password(request):
    username = request.POST["username"]
    email = request.POST["email"]
    password = request.POST["password"]
    print(username,email,password)
    sender_email = email
    rec_email = email

    count = len(CredentialsModel.objects.filter(email = email).filter(username= username))
    count_username = len(CredentialsModel.objects.filter(username= username))
    count_email = len(CredentialsModel.objects.filter(email = email))
    print(count)
    # return render(request, 'forget_password.html',)
    if  count > 0:
        from django.contrib.auth.models import User
        
        new_password = secrets.token_hex(10)
        password = password
        server = smtplib.SMTP('smtp.gmail.com', 25)
        server.starttls()

        try:
            server.login(sender_email, password)
            print("Login success")
            message = "Hey, this is your new password   " + new_password
            server.sendmail( sender_email , rec_email ,  message  )
            server.quit()


            user = User.objects.get( username = username )
            user.set_password(new_password)
            print ("change the password : ", new_password)
            user.save()
            print("Email has been sent to ", rec_email," message: ", message)

            return render(request, 'login.html',)
        except:
            print("error")
            context = { "message":"The gmail password is incorrect"}
            return render(request, 'forget_password.html', context)
    elif(count_username > 0):
        print("error")
        context = { "message":"The gmail address is incorrect"}
        return render(request, 'forget_password.html', context)
    else:
        print("error")
        context = { "message":"The username does not exist"}
        return render(request, 'forget_password.html', context)


def forget_password_page(request):
    return render(request, 'forget_password.html')

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        surveys = Survey.objects.filter(created_by=request.user).all()
        assigned_surveys = SurveyAssignment.objects.filter(assigned_to=request.user).all()

        context = {
          'surveys': surveys,
          'assgined_surveys': assigned_surveys
        }

        return render(request, 'survey/profile.html', context)
################################
#   GMAIL API IMPLEMENTATION   #
################################

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>


FLOW = flow_from_clientsecrets(
    settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
    scope=SCOPE,
    redirect_uri='http://127.0.0.1:8000/oauth2callback',
    prompt='consent')


def gmail_authenticate(request):
    print('***', 'views.gmail_authenticate', '***')
    print('***', 'request.user:', request.user, '***')

    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid:
        FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
                                                       request.user)
        print('***', "FLOW.params['state']:", FLOW.params['state'], '***')
        # if not xsrfutil.validate_token(settings.SECRET_KEY, FLOW.params['state'],
        #                            request.user):
        #     FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY, request.user)
        #     print('***', 'invalid state', '***')
        #     print('***', "FLOW.params['state']:", FLOW.params['state'], '***')
        # else:
        #     print('***', 'valid state', '***')
        authorize_url = FLOW.step1_get_authorize_url()
        # pdb.set_trace()
        return HttpResponseRedirect(authorize_url)
    else:
        http = httplib2.Http()
        http = credential.authorize(http)
        # service = build('gmail', 'v1', http=http)
        service = build('calendar', 'v3', credentials=credential)
        print('access_token = ', credential.access_token)
        status = True

        return render(request, 'index.html', {'user': request.user, 'status': status})


def auth_return(request):
    print('***', 'views.auth_return', '***')
    print('***', 'request.user:', request.user, '***')
    get_state = bytes(request.GET.get('state'), 'utf8')
    print('***', 'get_state:', get_state, '***')
    if not xsrfutil.validate_token(settings.SECRET_KEY, get_state,
                                   request.user):
        print('HttpResponseBadRequest()')
    credential = FLOW.step2_exchange(request.GET.get('code'))

    if request.user.is_authenticated:
        storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
        storage.put(credential)
        print('***', 'credential is saved', '***')

        credential = storage.get()
        service = build('calendar', 'v3', credentials=credential)
        email = service.calendars().get(calendarId='primary').execute()['summary']
        CredentialsModel.objects.filter(id=request.user).update(username=request.user.username,email=email,task=request.user.username)
        print('***', 'email is saved', '***')
    else:
        print('***', 'credential is NOT saved', '***')
    print("access_token: %s" % credential.access_token)
    return HttpResponseRedirect("/")

def eventList(request):
    print("***", "views.eventList", "***")
        # input = [ {id1:needHr1},{id2:needHr2} ]
    if request.method=="POST":
        today_eventIdList = [today_event['id'] for today_event in today_eventList]
        today_eventTypeList = [today_event['eventType'] for today_event in today_eventList]
        finishedEventIdList = request.POST.getlist('finishedEvent')
        remainHourList = request.POST.getlist('remainHour')
        eventStatusList = []    ## finish: 1  
        eventRemainHrsList = []
        print('finishedEventIdList', finishedEventIdList)
        print('remainHourList', remainHourList)
        remainHourList_index = 0
        eventRemainHrsList_index = 0

        for today_event in today_eventList:
            # print('remainHourList_index', remainHourList_index)
            # print('eventRemainHrsList_index', eventRemainHrsList_index)
            if today_event['id'] in finishedEventIdList:
                eventStatusList.append(1)
                eventRemainHrsList.append(0)
                eventRemainHrsList_index += 1
            else:
                eventStatusList.append(0)
                ## small or big ??
                if today_event['eventType'] == 0:
                    eventRemainHrsList.append(0)
                    eventRemainHrsList_index += 1
                elif today_event['eventType'] == 1:
                    eventRemainHrsList.append(remainHourList[remainHourList_index])
                    eventRemainHrsList_index += 1
                    remainHourList_index += 1
        print('today_eventIdList', today_eventIdList)
        print('today_eventTypeList', today_eventTypeList)
        print('eventStatusList', eventStatusList)
        print('eventRemainHrsList', eventRemainHrsList)
        result = PerformEventList(request,eventStatusList,today_eventIdList,eventRemainHrsList, today_eventTypeList)
        print(result)
        return HttpResponseRedirect("/")
    events = []
    if not request.user.is_authenticated:
        return redirect(reverse('register'))
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    try:
        access_token = credential.access_token
        resp, cont = Http().request(SCOPE,
                                    headers={'Host': 'www.googleapis.com',
                                            'Authorization': access_token})
        # now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        now = datetime.date.today()
        dateList = [now.month, now.day, now.year]
        timeMin, timeMax = getDateTimeBoundary(dateList)
        service = build('calendar', 'v3', credentials=credential)
        rm = ResourceManager(service)
        #events_result = service.events().list(calendarId='primary', timeMin=timeMin,
        #                                    timeMax=timeMax, singleEvents=True,
        #                                    orderBy='startTime').execute()
        #events = events_result.get('items', [])
        events = rm.get_all_events(timeMin, timeMax)
        today_eventList.clear()
        for event in events:
            today_eventList.append(event)
            event_name = event['summary']
            start_time = event['start']['dateTime']
            end_time = event['end']['dateTime']
            start_time = start_time.split("T")[1].split("+")[0]
            end_time = end_time.split("T")[1].split("+")[0]
            start_time = start_time[0:5]
            end_time = end_time[0:5]
            event.update({startTime_key: start_time})
            event.update({endTime_key: end_time})
            event.update({eventName_key: event_name})
            event.update({eventType_key: event['eventType']})
            print('abc = ', event['eventType'])
    except Exception as e:
        status = False
        print(e)
        print('Not Found')

    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname,'img': img , 'events': events}
    # context = {'user': request.user, 'events': events}
    return render(request, 'eventList.html', context)
    # action = None

    
def PerformEventList(request,status,Id,remainHr, today_eventTypeList):
    # The record has to be saved into dabase for summary module

    remainHr = [float(i) for i in remainHr]
    print(remainHr)
    eventNum = len(status)
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    user = User(service) 
    for i in range(eventNum):
        event = user.rm.get_one_event(Id[i])
        if status[i] == 1: # it is completed
            event['status'] = 1
            user.rm.update_event(event)
            continue
        name = event['summary']
        print(event['start']['dateTime'], event['deadline'])
        if name[-12:] == '_Preparation': # It is a non-complete preparation event
            #Find the preparation time range
            #timeRange = event['description'].split('\n')[1]
            #timeRange = timeRange.split()
            start = event['start']['dateTime'].split('+')[0].split('T')
            end = event['deadline']
            timeRange = start[0].split('-') + start[1].split(':')[:-1]
            timeRange += [end.year, end.month, end.day, end.hour, end.minute]
            print(timeRange)

            timeRange = list(map(int,timeRange)) # convert to int
            import os
            os.environ['TZ']='Asia/Taipei'
            now = datetime.datetime.now() 
            if timeRange[5] == now.year and timeRange[6] == now.month and timeRange[7] == now.day:
                print("Cannot reschedule preparation event in the future. Today is the last day.")
                return "Cannot reschedule preparation event in the future. Today is the last day."
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            tomorrow = datetime.datetime(tomorrow.year,tomorrow.month,tomorrow.day,0,0)
            timeRangeStart = datetime.datetime(timeRange[0],timeRange[1],timeRange[2],timeRange[3],timeRange[4])
            if tomorrow>timeRangeStart: 
                timeRange[0] = tomorrow.year
                timeRange[1] = tomorrow.month
                timeRange[2] = tomorrow.day
                timeRange[3] = tomorrow.hour
                timeRange[4] = tomorrow.minute

            tRange = {'start':timeRange[0:5], 'end':timeRange[5:10]}
            blankAndEvent = user.algo.FindBlankBlock(tRange, user.pref)
            AssignEvent = { 
                'EventName' : event['summary'],
                #'Priority' : ?,
                'PreparingTime' : {
                    'Start' : tRange['start'],
                    'End'   : tRange['end'],
                    'PreparingHours' : event['PreparingHours']
                }
            }
            if 'description' in event:
                AssignEvent['description'] = event['description']
            eventListHr = remainHr[i]
            AssignEvent['EventName'] = AssignEvent['EventName'].replace('Big_','')
            AssignEvent['EventName'] = AssignEvent['EventName'].replace('_Preparation','')
            print("\n\nAssignEvent ",AssignEvent)
            return user.algo.AssignBlock(AssignEvent,blankAndEvent,tRange,user.pref,user.service,eventListHr)




def createEvent(request):
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user.username
    context = {'user': nickname, 'img': img}
    return render(request, 'createEvent.html', context)

def update_profile(request):
    print('***', 'views.update_profile', '***')
    print('***', 'request.user:', request.user, '***')
    from django.contrib.auth.models import User

    nickname = request.POST.get( "nickname" )
    password = request.POST.get( "password" )
    confirmpsd = request.POST.get( "confirmpsd" )
    user_img = request.FILES.get('photo')


    ###chick photo#####
    print("user_img  :  " ,user_img)
    if user_img != None:
        #CredentialsModel.objects.filter(id = request.user).update(user_image= user_img)
        img = CredentialsModel.objects.get(id = request.user)
        img.user_image = user_img
        img.save()

    ##chick nickname####
    if nickname == "" or  nickname.isspace():
        print ("request.user : ",request.user)
    else:
        CredentialsModel.objects.filter(id = request.user).update(task = nickname)
        nickname = CredentialsModel.objects.filter(id = request.user)[0].task
        print("nickname_change :", nickname)


    ####chick password####
    if password == confirmpsd  and password != "" and confirmpsd != "" :
        print("username , password: ", request.user, password)
        user = User.objects.get( username = request.user )
        user.set_password(password)
        user.save()
        user = authenticate(username=request.user.username, password=password)
        if user is not None and user.is_active:
            login(request, user)
        # return HttpResponseRedirect("/login/")
        return HttpResponseRedirect("/profile/")

    else:
        print("password non completed !")
        return HttpResponseRedirect("/profile/")

def profile(request):
    print('***', 'views.profile', '***')
    print('***', 'request.user:', request.user , '***')
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user.username
    context = {'user': nickname, 'img': img}
    return render(request, 'profile.html', context)

def summary(request):
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    context = {'user': nickname, 'img': img}
    return render(request, 'summary.html', context)

def setting(request):
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    context = {'user': nickname, 'img': img}
    return render(request, 'setting.html', context)

#def GetGooEventFormat()
'''
event = {
          'summary': '測試',
          'id': '1234gsfhdf567sss',
          'start': {
            'dateTime': '2019-12-12T2:00:00-00:00',
            #'timeZone': 'Asia/Taipei',
          },
          'end': {
            'dateTime': '2019-12-12T5:00:00-00:00',
            #'timeZone': 'Asia/Taipei',
          },
          #'colorId' : 3,
        }
'''
def createSmallEvent(request): 
    if request.method=="POST":
        storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
        credential = storage.get()
        service = build('calendar', 'v3', credentials=credential)
        user = User(service)

        gooEvent = {}
        gooEvent['summary'] = request.POST["eventName"]

        start = request.POST["startTime"]  # format:2019-12-27T02:00
        end = request.POST["endTime"] 
        #print('start='+start)
        startList = [int(start[0:4]),int(start[5:7]),int(start[8:10]),int(start[11:13]),int(start[14:16])]
        endList = [int(end[0:4]),int(end[5:7]),int(end[8:10]),int(end[11:13]),int(end[14:16])]
        utcStart = user.algo.GetUTCtimezone(startList)
        utcEnd = user.algo.GetUTCtimezone(endList)
        #print('utcStart='+utcStart)
        gooEvent['start'] = {'dateTime':utcStart}
        gooEvent['end'] = {'dateTime':utcEnd}
        gooEvent['eventType'] = 0
        gooEvent['status'] = 0
        gooEvent['description'] = request.POST["description"]
        gooEvent['location'] = request.POST["location"]
        gooEvent['colorId'] = 10
        print('gooEvent=',gooEvent)
        
        if user.algo.DetectConflict(startList,endList):
            print("This small event has conflict with other event. Please select other time.")
        else:
            user.rm.insert_event(gooEvent)
            #user.service.events().insert(calendarId='primary', body=gooEvent).execute()
        return HttpResponseRedirect("/")
        
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img': img}
    # context = {'user': request.user}
    return render(request, 'createSmallEvent.html', context)


def createBigEvent(request):
    if request.method=="POST":
        storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
        credential = storage.get()
        service = build('calendar', 'v3', credentials=credential)
        user = User(service)
        rm = ResourceManager(service)

        # Input
        eventForAssignBlock = {}
        eventForAssignBlock['EventName'] = request.POST["eventName"]
        eventForAssignBlock['Description'] = request.POST['description']
        if eventForAssignBlock['Description'] == '':
            eventForAssignBlock['Description'] = 'None'
        eventForAssignBlock['Priority'] = int(request.POST['priority'])

        DRange = request.POST['dateRange'] # 12/20/2019 - 12/23/2019
        prepStartFrom = [int(DRange[6:10]),int(DRange[0:2]),int(DRange[3:5])]
        import os
        os.environ['TZ']='Asia/Taipei'
        now = datetime.datetime.now()
        print('now',now)
        if now.year == prepStartFrom[0] and now.month == prepStartFrom[1] and now.day == prepStartFrom[2]: # Start from today
            prepStartFrom.extend([now.hour,now.minute]) # the starting hr and minutes begin from tnow
        else: # start after today
            prepStartFrom.extend([0,0])
        prepStartTo   = [int(DRange[19:23]),int(DRange[13:15]),int(DRange[16:18]),23,59]
        prepHr = int(request.POST['preparingHours'])
        eventForAssignBlock['PreparingTime'] = {
            'Start': prepStartFrom, 'End': prepStartTo, 'PreparingHours': prepHr}

        GetFinalStart = request.POST["startTime"]  # format:2019-12-27T02:00
        GetFinalEnd = request.POST["endTime"] 
        if GetFinalStart != '':
            FinalEventStart = [int(GetFinalStart[0:4]),int(GetFinalStart[5:7]),int(GetFinalStart[8:10]),int(GetFinalStart[11:13]),int(GetFinalStart[14:16])]
            FinalEventEnd = [int(GetFinalEnd[0:4]),int(GetFinalEnd[5:7]),int(GetFinalEnd[8:10]),int(GetFinalEnd[11:13]),int(GetFinalEnd[14:16])]
            if prepStartTo[:3] == FinalEventStart[:3] : # the last day of preparation equals to the first day of final event
                prepStartTo[3:5] = FinalEventStart[3:5] # the preparation can not be latter than final event
            location = request.POST["location"]
            eventForAssignBlock['FinalEvent'] = {
                'Start': FinalEventStart, 'End': FinalEventEnd, 'Location': location}
        #print('eventForAssignBlock ',eventForAssignBlock)

        # Find blank block
        timeRange = {'start':prepStartFrom, 'end':prepStartTo }
        blankAndEvent = user.algo.FindBlankBlock(timeRange, user.pref)
        #print('blankAndEvent',blankAndEvent)
        # Assign blank block
        print(user.algo.AssignBlock(eventForAssignBlock,blankAndEvent,timeRange,user.pref,user.service,0))
    
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img':img}
    # context = {'user': request.user}
    return render(request, 'createBigEvent.html', context)

def EditSmallEvent(request):
    asd=1


def DeleteEvent(id):
    asd =1



def editEvent(request):
    print("***", "views.editEvent", "***")
    events = []
    if request.method=="POST":
        print("***", "views.editEvent", "POST", "***")
        print(request.POST)
        dateString = request.POST["date"]
        dateList = dateString.split('/')
        # print("dateList", dateList)
        timeMin, timeMax = getDateTimeBoundary(dateList)
        storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
        credential = storage.get()
        service = build('calendar', 'v3', credentials=credential)
        rm = ResourceManage(service)
        #events_result = service.events().list(calendarId='primary', timeMin=timeMin,
        #                                timeMax=timeMax, singleEvents=True,
        #                                orderBy='startTime').execute()
        #events = events_result.get('items', [])
        events = rm.get_all_events(timeMin, timeMax)
        for event in events:
            event_name = event['summary']
            event.update({eventName_key: event_name.split('_')[1]})
            start_time = event['start']['dateTime']
            end_time = event['end']['dateTime']
            start_time = start_time.split("T")[1].split("+")[0]
            end_time = end_time.split("T")[1].split("+")[0]
            start_time = start_time[0:5]
            end_time = end_time[0:5]
            event.update({startTime_key: start_time})
            event.update({endTime_key: end_time})
            prefix = event_name.split('_')[0]
            if prefix == "Big":
                event.update({eventType_key: 1})
            elif prefix == "Small":
                event.update({eventType_key: 0})
            else:
                event.update({eventType_key: -1})

    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img':img, 'events': events}
    # context = {'user': request.user, 'events': events}
    return render(request, 'editEvent.html', context)


def editBigEvent(request, event_id):

    if request.method=="POST":
        EditBigEvent(request, event_id)
    print("event id", event_id)
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    event_name = event['summary']
    event.update({eventName_key: event_name.split('_')[1]})
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img':img, 'event': event}
    return render(request, 'editBigEvent.html', context)


def GetBigEventEdit(request):
    editEvent = {}
    editEvent['EventName'] = request.POST["eventName"]
    editEvent['Description'] = request.POST['description']
    editEvent['Priority'] = int(request.POST['priority'])

    DRange = request.POST['dateRange'] # 12/20/2019 - 12/23/2019
    prepStartFrom = [int(DRange[6:10]),int(DRange[0:2]),int(DRange[3:5])]
    import os
    os.environ['TZ']='Asia/Taipei'
    now = datetime.datetime.now()
    #print(now)
    if now.year == prepStartFrom[0] and now.month == prepStartFrom[1] and now.day == prepStartFrom[2]: # Start from today
        prepStartFrom.extend([now.hour,now.minute]) # the starting hr and minutes begin from tnow
    else: # start after today
        prepStartFrom.extend([0,0])
    prepStartTo   = [int(DRange[19:23]),int(DRange[13:15]),int(DRange[16:18]),23,59]
    prepHr = int(request.POST['preparingHours'])
    editEvent['PreparingTime'] = {
        'Start': prepStartFrom, 'End': prepStartTo, 'PreparingHours': prepHr}

    GetFinalStart = request.POST["startTime"]  # format:2019-12-27T02:00
    GetFinalEnd = request.POST["endTime"] 
    if GetFinalStart != '':
        FinalEventStart = [int(GetFinalStart[0:4]),int(GetFinalStart[5:7]),int(GetFinalStart[8:10]),int(GetFinalStart[11:13]),int(GetFinalStart[14:16])]
        FinalEventEnd = [int(GetFinalEnd[0:4]),int(GetFinalEnd[5:7]),int(GetFinalEnd[8:10]),int(GetFinalEnd[11:13]),int(GetFinalEnd[14:16])]
        if prepStartTo[:3] == FinalEventStart[:3] : # the last day of preparation equals to the first day of final event
            prepStartTo[3:5] = FinalEventStart[3:5] # the preparation can not be latter than final event
        location = request.POST["location"]
        editEvent['FinalEvent'] = {
            'Start': FinalEventStart, 'End': FinalEventEnd, 'Location': location}
    #print('eventForAssignBlock ',eventForAssignBlock)
    return editEvent


def DeleteInvalidPrepEvent(user, From, To, idEvent,needMoreMin, deleteId):
    From = user.algo.GetUTCtimezone(From)
    To = user.algo.GetUTCtimezone(To)
    #print(From,'  ',To)
    
    if To > From: 
        preEvent = user.service.events().list(calendarId='primary',
         timeMin=From, timeMax=To, singleEvents=True).execute()
        
        preEvent = preEvent.get('items', [])
        for e in preEvent:
            if e['summary'] == 'Big_' + idEvent['summary'] + "_Preparation":
                st, et = e['start']['dateTime'], e['end']['dateTime']
                start =  dateutil.parser.parse(st)
                end = dateutil.parser.parse(et)
                ts = (end - start).total_seconds() / 60; 
                needMoreMin += ts
                print("delete ",e)
                deleteId.append(e['id'])
                
    return needMoreMin


def EditBigEvent(request, event_id):
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    user = User(service)
    #input

    editEvent = GetBigEventEdit(request)
    #print("\n\nedit\n", editEvent)
    print("editEvent ",editEvent)
    idEvent = user.service.events().get(calendarId='primary', eventId=event_id).execute()
    print("\n\nidEvent",idEvent)
    #print(event_id,idEvent)
    idEvent['summary'] = idEvent['summary'].replace("Big_",'')
    idEvent['summary'] = idEvent['summary'].replace("_Preparation",'')
    # Get origin data. Brute force search.   
    lastYear = (datetime.datetime.utcnow() - datetime.timedelta(days=8)).isoformat() + 'Z'
    nextYear = (datetime.datetime.utcnow() + datetime.timedelta(days=8)).isoformat() + 'Z'
    events = user.service.events().list(
        calendarId='primary', timeMin=lastYear, timeMax=nextYear,
        singleEvents=True, orderBy='startTime').execute()
    events = events.get('items', [])
    gooFinalEvent = None
    for e in events:
        if "Big_" + idEvent['summary'] + "_Preparation" == e['summary']:
            findEvent = e
        if "Big_" + idEvent['summary'] == e['summary']:
            gooFinalEvent = e
    # preapration hr需要更多或更少小時
    gooPrepHr = int(findEvent['description'].split('\n')[2])
    needMoreHr = editEvent['PreparingTime']['PreparingHours'] - gooPrepHr 
    needMoreMin = needMoreHr*60
    print("prepHr",needMoreMin)
    
    # 移除不在timeRange的未來prep事件(start延後、end提前)
    strPrepRange = findEvent['description'].split('\n')[1] 
    oriPrepRange = [int(i) for i in strPrepRange.split()] # [2019, 12, 24, 0, 0, 2019, 12, 27, 23, 59]
    # Delete prep event before new preparation start time (start 延後)
    deleteId = []
    newPrepStart = editEvent['PreparingTime']['Start']
    needMoreMin = DeleteInvalidPrepEvent(
        user, oriPrepRange[0:5], newPrepStart, idEvent, needMoreMin, deleteId)
    print("start 延後",needMoreMin)
    # Delete prep event adter new preparation end time (end 提前)
    newPrepEnd =  editEvent['PreparingTime']['End']
    needMoreMin = DeleteInvalidPrepEvent(
        user, newPrepEnd, oriPrepRange[5:10], idEvent, needMoreMin, deleteId)
    print("end 提前",needMoreMin)
    #其他非時間的改動: eventName, description
    prepRange = newPrepStart + newPrepEnd
    strPrep  = ""
    for i in prepRange:
        strPrep += str(i) + ' ' 
    editEvent['Description'] += '\n' + strPrep
    editEvent['Description'] += '\n' + str(editEvent['PreparingTime']['PreparingHours'])
    #editEvent['EventName'] =  editEvent['EventName'] 
    # Check final event
    hasDeleted = False
    if gooFinalEvent!= None and 'FinalEvent' in editEvent: 
        user.service.events().delete(calendarId='primary', eventId=gooFinalEvent['id']).execute()
        print("hasDelted 794")
        hasDeleted = True
        finalStart = gooFinalEvent['start']['dateTime'] 
        finalEnd = gooFinalEvent['end']['dateTime'] # 2019-12-28T08:00:00+08:00
        print(finalStart,finalEnd)
        listFinStart = [int(finalStart[0:4]), int(finalStart[5:7]), int(finalStart[8:10]), int(finalStart[11:13]), int(finalStart[14:16])]
        listFinEnd = [int(finalEnd[0:4]), int(finalEnd[5:7]), int(finalEnd[8:10]), int(finalEnd[11:13]), int(finalEnd[14:16])]
        if user.algo.DetectConflict(listFinStart,listFinEnd) : 
            print("Cannot modify final event")
            gooFinalEvent = removeID(gooFinalEvent)
            user.service.events().insert(calendarId='primary', body=gooFinalEvent).execute()
            return "Cannot modify final event"
    elif gooFinalEvent!= None and 'FinalEvent' not in editEvent: # 原本有final event，後來使用者不要
        user.service.events().delete(calendarId='primary', eventId=gooFinalEvent['id']).execute()
        hasDeleted = True
        print("hasDelted 809")
    # 根據start 延後,end 提前 ，看總共要新增或減少多少prepration event，
    # 再用findBlankBlock然後AssignBlock
    tRange = {'start':editEvent['PreparingTime']['Start'],
                  'end':editEvent['PreparingTime']['End'] }
    utcNewPrepStart = user.algo.GetUTCtimezone(newPrepStart)
    utcNewPrepEnd   = user.algo.GetUTCtimezone(newPrepEnd)
    blankAndEvent = user.algo.FindBlankBlock(tRange, user.pref)
    if needMoreMin >= 0:  # Add prep events
        #print('blank ',blankAndEvent)
        if needMoreMin > 0:
            result = user.algo.AssignBlock(editEvent,blankAndEvent,tRange,user.pref,user.service,needMoreMin/60)
        elif needMoreMin == 0:
            result = user.algo.AssignBlock(editEvent,blankAndEvent,tRange,user.pref,user.service,-1)
        #print("In editing big event, ",result)
        if result != "Add big event Successfully.": # restore the deleted final event
            if hasDeleted == True:
                gooFinalEvent = removeID(gooFinalEvent)
                user.service.events().insert(calendarId='primary', body=gooFinalEvent).execute()
            print("Failed. " + result)
            return "Failed. " + result
    elif needMoreMin < 0: # Delete prep events
        if 'FinalEvent' in editEvent:
            start = user.algo.GetUTCtimezone(editEvent['FinalEvent']['Start'])
            end = user.algo.GetUTCtimezone(editEvent['FinalEvent']['End'])
            finalEvent = {
                'summary': "Big_" + editEvent['EventName'],
                'description': editEvent['Description'],
                'location' : editEvent['FinalEvent']['Location'],
                'start' : {'dateTime': start} ,
                'end' : {'dateTime': end},
                'colorId' : 11
            }

            user.service.events().insert(calendarId='primary', body=finalEvent).execute()


        deleteE = user.service.events().list(calendarId='primary', 
            timeMin=utcNewPrepStart, timeMax=utcNewPrepEnd, singleEvents=True, orderBy='startTime').execute()
        deleteE = deleteE.get('items', [])
        for e in deleteE:
            if e['summary'] == 'Big_' + idEvent['summary'] + "_Preparation":
                st, et = e['start']['dateTime'], e['end']['dateTime']
                start =  dateutil.parser.parse(st)
                end = dateutil.parser.parse(et)
                ts = (end - start).total_seconds() / 60; 
                if -ts >= needMoreMin:
                    needMoreMin += ts
                    user.service.events().delete(calendarId='primary', eventId=e['id']).execute()
                else:
                    newEndTime = end + datetime.timedelta(minutes=needMoreMin)
                    listEndTime = [newEndTime.year,newEndTime.month,newEndTime.day,newEndTime.hour,newEndTime.minute]
                    newUTCEndTime = user.algo.GetUTCtimezone(listEndTime) 
                    e['end']['dateTime'] = newUTCEndTime
                    e['start']['dateTime'] = user.algo.GetUTCtimezone([start.year, start.month, start.day, start.hour, start.minute]) 
                    #print('\n\nHi',e['start']['dateTime'],e['end']['dateTime'])
                    user.service.events().update(calendarId='primary', eventId=e['id'], body=e).execute()
                    needMoreMin = 0
                if needMoreMin == 0:
                    break
    # update original prep events between the new prep start and prep end
    updateE = user.service.events().list(calendarId='primary', 
        timeMin=utcNewPrepStart, timeMax=utcNewPrepEnd, singleEvents=True).execute()
    updateE = updateE.get('items', [])
    for e in updateE:
        if e['summary'] == "Big_" + idEvent['summary'] + "_Preparation":
            e['summary'] = "Big_" + editEvent['EventName'] + "_Preparation"
            e['description'] = editEvent['Description']
            user.service.events().update(calendarId='primary', eventId=e['id'], body=e).execute()
    # Delete original event outside of the new prep start and prep end
    for Id in deleteId:
        user.service.events().delete(calendarId='primary', eventId=Id).execute()

    print("Edit big event successfully.")
    return "Edit big event successfully."



# def editSmallEvent(request, event_id):
#     storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
#     credential = storage.get()
#     service = build('calendar', 'v3', credentials=credential)
#     user = User(service)



def removeID(oriEvent):
    event = {}
    event['summary'] = oriEvent['summary']
    if 'description' in oriEvent:
        event['description'] = oriEvent['description']
    if 'location' in oriEvent['location']:
        event['location'] =  oriEvent['location']
    event['start']= {'dateTime': oriEvent['start']['dateTime']}
    event['end'] =  {'dateTime': oriEvent['end']['dateTime']}
    return event
    
def editEvent(request):
    print("***", "views.editEvent", "***")
    events = []
    if request.method=="POST":
        print("***", "views.editEvent", "POST", "***")
        print(request.POST)
        dateString = request.POST["date"]
        dateList = dateString.split('/')
        # print("dateList", dateList)
        timeMin, timeMax = getDateTimeBoundary(dateList)
        storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
        credential = storage.get()
        service = build('calendar', 'v3', credentials=credential)
        #events_result = service.events().list(calendarId='primary', timeMin=timeMin,
        #                                timeMax=timeMax, singleEvents=True,
        #                                orderBy='startTime').execute()
        #events = events_result.get('items', [])
        rm = ResourceManager(service)
        events = rm.get_all_events(timeMin, timeMax)
        for event in events:
            print(event)
            event_name = event['summary']
            event.update({eventName_key: event_name})
            start_time = event['start']['dateTime']
            end_time = event['end']['dateTime']
            start_time = start_time.split("T")[1].split("+")[0]
            end_time = end_time.split("T")[1].split("+")[0]
            start_time = start_time[0:5]
            end_time = end_time[0:5]
            event.update({startTime_key: start_time})
            event.update({endTime_key: end_time})
            event_name = event['summary']
            eventType = rm.get_eventType(event['id'])
            event.update({eventType_key: eventType})
            print('abc = ', event['eventType'])
            
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img':img, 'events': events}
    # context = {'user': request.user, 'events': events}
    return render(request, 'editEvent.html', context)

# def editBigEvent(request, event_id):
#     if request.method=="POST":
#         EditBigEvent(request, event_id)
#     print("event id", event_id)
#     storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
#     credential = storage.get()
#     service = build('calendar', 'v3', credentials=credential)
#     event = service.events().get(calendarId='primary', eventId=event_id).execute()
#     event_name = event['summary']
#     event.update({eventName_key: event_name.split('_')[1]})
#     nickname = CredentialsModel.objects.filter(id = request.user)[0].task
#     img = CredentialsModel.objects.filter(id = request.user)[0].user_image
#     if nickname == None:
#         nickname = request.user
#     context = {'user': nickname, 'img':img, 'event': event}
#     return render(request, 'editBigEvent.html', context)

def editSmallEvent(request, event_id):
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    user = User(service)

    if request.method=="POST":
        newS, startList, endList = GetNewSmallEvent(request,user)
        oriS = user.service.events().get(calendarId='primary',eventId=event_id).execute()
        user.rm.delete_event(event_id, flag=1)
        if user.algo.DetectConflict(startList,endList):
            oriS = removeID(oriS)
            user.rm.insert_event(oriS)
            #user.service.events().insert(calendarId='primary',body=oriS, colorId = 10).execute() # restore original event
            print("This small event has conflict with other event. Please select other time.")
        else:
            # New Name
            user.rm.insert_event(newS)
            #user.service.events().insert(calendarId='primary', body=newS).execute()
        return HttpResponseRedirect("/")
    
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    start_dateTime = event['start']['dateTime'].split('+')[0][:-3]
    end_dateTime = event['end']['dateTime'].split('+')[0][:-3]
    event_name = event['summary']
    event.update({eventName_key: event_name})
    event.update({start_dateTime_key: start_dateTime})
    event.update({end_dateTime_key: end_dateTime})
    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img': img , 'event': event}
    return render(request, 'editSmallEvent.html', context)

def GetNewSmallEvent(request, user):
    newS = {}
    newS['summary'] = request.POST["eventName"]
    start = request.POST["startTime"]  # format:2019-12-27T02:00
    end = request.POST["endTime"]
    #print('start='+start)
    startList = [int(start[0:4]),int(start[5:7]),int(start[8:10]),int(start[11:13]),int(start[14:16])]
    endList = [int(end[0:4]),int(end[5:7]),int(end[8:10]),int(end[11:13]),int(end[14:16])]
    utcStart = user.algo.GetUTCtimezone(startList)
    utcEnd = user.algo.GetUTCtimezone(endList)
    #print('utcStart='+utcStart)
    newS['start'] = {'dateTime':utcStart}
    newS['end'] = {'dateTime':utcEnd}
    newS['description'] = request.POST["description"]
    newS['location'] = request.POST["location"]
    newS['status'] = 0
    newS['eventType'] = 0
    newS['colorId'] = 10
    #print('newS=',newS)
    return newS, startList, endList


def removeID(oriEvent):
    event = {}
    event['summary'] = oriEvent['summary']
    event['description'] = oriEvent['description']
    event['location'] =  oriEvent['location']
    #event['status'] = 0
    #event['eventType'] = 0
    event['start']= {'dateTime': oriEvent['start']['dateTime']}
    event['end'] =  {'dateTime': oriEvent['end']['dateTime']}
    return event

def deleteSmallEvent(request, event_id):
    print("***", "deleteSmallEvent", "***")
    print("event_id", event_id)
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    pref = Preference()
    rm = ResourceManager(service)
    algo = ScheduleAlgorithm(service)
    event = rm.get_one_event(event_id)
    rm.delete_event(event_id, pref)
    algo.TimeShift(pref, event['start']['dateTime'])
    #service.events().delete(calendarId='primary', eventId=event_id).execute()
    return HttpResponseRedirect("/")

def deleteBigEvent(request,event_id):
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    #service.events().delete(calendarId='primary', eventId=event_id).execute()
    user = User(service)
    rm = ResourceManager(service)
    find = rm.get_one_event(event_id)
    rm.delete_event(event_id)
    #find = user.service.events().get(calendarId='primary', eventId=event_id).execute()
    #start = find['start']['dateTime'].split('+')[0].split('T')
    end = find['deadline']
    #prep = start[0].split('-') + start[1].split(':')[:-1]
    now = datetime.datetime.today()
    prep = [now.year, now.month, now.day, now.hour, now.minute]
    prep += [end.year, end.month, end.day, end.hour, end.minute]
    #prep = event['description'].split('\n')[1]
    prep = [int(i) for i in prep]
    print(prep)
    listStart = prep[0:5]
    listEnd   = prep[5:10]
    utcFrom = user.algo.GetUTCtimezone(listStart)
    utcTo =  user.algo.GetUTCtimezone(listEnd)
    # delete prep event
    event = rm.get_preparation_event(event_id, utcFrom, utcTo)
    for e in event:
        rm.delete_event(e['id'])
    #event = user.service.events().list(calendarId='primary', 
    #    timeMin=utcFrom,timeMax=utcTo, singleEvents=True).execute()
    #event = event.get('items', [])
    #for e in event:
    #    if e['summary'] == find['summary']:
    #        user.service.events().delete(calendarId='primary', eventId=event_id).execute()
    # delete final event
    #utcFrom = utcTo
    #listEnd[0] += 1 # add one year
    #utcTo =  user.algo.GetUTCtimezone(listEnd)
    #event = user.service.events().list(calendarId='primary', 
    #    timeMin=utcFrom,timeMax=utcTo, singleEvents=True, orderBy='startTime').execute()
    #event = event.get('items', [])
    #for e in event:
    #    if e['summary'] + "_Preparation" == find['summary']:
    #        user.service.events().delete(calendarId='primary', eventId=event_id).execute()
    #        break # only one final event

    return HttpResponseRedirect("/")

def SerachBigEventInfo(request, event_id):
    storage = DjangoORMStorage(CredentialsModel, 'id', request.user, 'credential')
    credential = storage.get()
    service = build('calendar', 'v3', credentials=credential)
    user = User(service)
    
    targetEvent = user.service.events().get(calendarId='primary', eventId=event_id).execute()
    targetEvent['summary'] = targetEvent['summary'].replace("Big_",'')
    targetEvent['summary'] = targetEvent['summary'].replace("_Preparation",'')
 
    prepE,finalE = [],{}
    lastYear = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).isoformat() + 'Z'
    nextYear = (datetime.datetime.utcnow() + datetime.timedelta(days=365)).isoformat() + 'Z'
    yearE = user.service.events().list(calendarId='primary', 
        timeMin=lastYear,timeMax=nextYear, singleEvents=True,orderBy='startTime').execute()
    yearE = yearE.get('items', [])
    for e in yearE:
        if e['summary'] == "Big_" + targetEvent['summary'] + "_Preparation" :
            prepE.append(e)
        elif e['summary'] == "Big_" + targetEvent['summary']:
            finalE = e
            break
    return prepE, finalE




def getDateTimeBoundary(dateList):
    year = int(dateList[2])
    month = int(dateList[0])
    day = int(dateList[1])

    timeMinList = [year, month, day, 0, 0]
    timeMin = getUTCtime(timeMinList)
    timeMaxList = [year, month, day, 23, 59]
    timeMax = getUTCtime(timeMaxList)
    return (timeMin, timeMax)

def getUTCtime(timeList):
    tw = pytz.timezone('Asia/Taipei')
    timeString = datetime.datetime(timeList[0],timeList[1],timeList[2],timeList[3],timeList[4])
    timeString = tw.localize(timeString)
    timeString = timeString.astimezone(pytz.utc).isoformat()
    timeString = timeString[:-6] + 'Z'
    utcTimeString = timeString
    return utcTimeString
    
def showsummary(request):
    start, end = request.POST['dateRange'].split(' - ')
    month, day, year = [int(j) for j in start.split('/')]
    handler = Summary()
    start = handler.GetUTCtimezone([year, month, day, 0, 0])

    month, day, year = [int(j) for j in end.split('/')]
    end = handler.GetUTCtimezone([year, month, day, 23, 59])

    nickname = CredentialsModel.objects.filter(id = request.user)[0].task
    img = CredentialsModel.objects.filter(id = request.user)[0].user_image
    if nickname == None:
        nickname = request.user
    context = {'user': nickname, 'img': img }
    print(start, end)
    x = handler.get_completion_rate(start, end)
    context['late'] = x[0]
    context['complete'] = x[1]
    context['late_big'] = x[2]
    context['late_small'] = x[3]
    context['complete_big'] = x[4]
    context['complete_small'] = x[5]
    print(x)
    return render(request, 'showSummary.html', context)
