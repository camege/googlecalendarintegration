from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import json


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']
API_TOKEN = ""
BASE_URL = "https://kolayik.com/api/v2/"
LIST_URL = "person/list"
VIEW_URL = "person/view"
HEADER = dict(Authorization='Bearer ' + API_TOKEN)
NOW = datetime.datetime.utcnow()+ datetime.timedelta(hours=3)
PLUS_EIGHT_DAYS = NOW + datetime.timedelta(days=7)
LEAVE_URL = "leave/list?status=approved&startDate=" + NOW.isoformat() + "&endDate=" + PLUS_EIGHT_DAYS.isoformat() + "&limit=1000"
CANCELLED_LEAVE_URL = "leave/list?status=cancelled&startDate=" + NOW.isoformat() + "&endDate=" + PLUS_EIGHT_DAYS.isoformat() + "&limit=1000"

def make_request(method, url, payload):
    response = requests.request(method, url, headers=HEADER, data=payload)
    return json.loads(response.text)

def get_employees():
    person_list = []
    temp = 0
    last = 1
    while temp < last:
        response = make_request("POST", BASE_URL + LIST_URL, {'status': 'active'})
        if not response['error']:
            temp = (response['data']['currentPage'])
            last = (response['data']['lastPage'])
            for item in response['data']['items']:
                people = make_request("GET", BASE_URL + VIEW_URL + "/" + item['id'], {})
                person = {'email':people['data']['person']['workEmail'], 'name': item['firstName'] + " " + item['lastName'], 'id': item['id']}
                person_list.append(person)
        else:
            print(response["code"], response["message"])
        temp += 1
    return person_list

def get_leaves(person_list,status):
    print(NOW, PLUS_EIGHT_DAYS)
    response = make_request("GET", status, {})
    leaves = []
    for item in response['data']:
        try:
            email = next(items['email'] for items in person_list if items["id"] == item['person']['id'])
            leave = {'email': email, 'event_startdate': item['startDate'], 'event_endDate': item['endDate']}
            leaves.append(leave)
        except StopIteration:
            print("Empty list")
    return leaves

def send_leaves_to_gcalendar(leaves):
    service = enable_google_service()
    real_now = datetime.datetime.utcnow().isoformat() + 'Z'
    print(leaves)
    for x in leaves:
        event_id = (x['email'] + x['event_startdate'] + x['event_endDate']).replace(" ", "")
        events_result = service.events().list(calendarId=x['email'], timeMin=real_now, q=event_id,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        if not (events_result['items']):
            event = {
                'summary': 'OOO',
                'description': event_id,
                'start': {
                    'dateTime': datetime.datetime.strptime(x['event_startdate'], "%Y-%m-%d %H:%M:%S").isoformat(),
                    'timeZone': 'Asia/Istanbul',
                },
                'end': {
                    'dateTime': datetime.datetime.strptime(x['event_endDate'], "%Y-%m-%d %H:%M:%S").isoformat(),
                    'timeZone': 'Asia/Istanbul',
                },
                'attendees': [
                    {'email': x['email'],
                     'responseStatus': 'accepted'},
                ]
            }

            event = service.events().insert(calendarId='out-of-office@kolayik.com', body=event,
                                            sendUpdates='all').execute()
            print('Event created: %s' % (event.get('htmlLink')))
        else:
            print("Error")

def cancel_cancelled_leaves(cancelled_leaves):
    print(cancelled_leaves)
    service = enable_google_service()
    for x in cancelled_leaves:
        event_id = (x['email'] + x['event_startdate'] + x['event_endDate']).replace(" ", "")
        cancelled_result = service.events().list(calendarId=x['email'], timeMin=real_now, q=event_id,
                                                 maxResults=10, singleEvents=True,
                                                 orderBy='startTime').execute()

        if (cancelled_result['items']):
            google_event_id = cancelled_result['items'][0]['id']
            service.events().delete(calendarId=<EMAIL>, eventId=google_event_id,
                                    sendUpdates='all').execute()
        else:
            print(event_id + ' already not on calendar')

def enable_google_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


employees = get_employees()
leaves = get_leaves(employees, BASE_URL+LEAVE_URL)
cancelled_leaves = get_leaves(employees, BASE_URL + CANCELLED_LEAVE_URL)
send_leaves_to_gcalendar(leaves)
cancel_cancelled_leaves(cancelled_leaves)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
