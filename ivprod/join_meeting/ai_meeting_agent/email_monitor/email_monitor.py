import os
import base64
import json
import re
from flask import Flask, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from flask_socketio import SocketIO
from flask_cors import CORS
from icalendar import Calendar
import logging

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app)

def authenticate_gmail():
    print("Authenticating Gmail...")
    """Authenticate and return the Gmail service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("Using existing credentials.")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("Credentials refreshed.")
        else:
            print("No valid credentials found. Starting authentication flow.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            print("Flow created, running local server for authentication...")
            creds = flow.run_local_server(port=61372)  # Change to the authorized port
            print("Authentication successful.")
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Credentials saved to token.json.")
    return build('gmail', 'v1', credentials=creds)

def extract_meeting_details(message):
    """Extract all relevant details from the email message."""
    details = {}
    payload = message['payload']
    headers = payload['headers']

    # Extract all headers
    for header in headers:
        if header['name'] == 'Subject':
            details['title'] = header['value']
        elif header['name'] == 'Date':
            details['date'] = header['value']
        elif header['name'] == 'From':
            details['from'] = header['value']
        elif header['name'] == 'To':
            details['to'] = header['value']
        elif header['name'] == 'Cc':
            details['cc'] = header['value']

    # Extract the body of the email
    if 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        details['body'] = body  # Store the entire body for inspection

        # Extract meeting link
        meeting_link_match = re.search(r'Meeting link\s*(https?://[^\s]+)', body)
        if meeting_link_match:
            details['link'] = meeting_link_match.group(1)

        # Extract date and time
        date_time_match = re.search(r'When\s*:\s*(.*)', body, re.IGNORECASE)
        if date_time_match:
            details['date_time'] = date_time_match.group(1).strip()

        # Extract guests
        guests_match = re.search(r'Guests?\s*:\s*(.*)', body, re.IGNORECASE)
        if guests_match:
            details['guests'] = [guest.strip() for guest in guests_match.group(1).split(',') if guest.strip()]

        # Extract attendees from the body if they are explicitly mentioned
        attendees_match = re.search(r'Attendees?\s*:\s*(.*)', body, re.IGNORECASE)
        if attendees_match:
            details['attendees'] = [attendee.strip() for attendee in attendees_match.group(1).split(',') if attendee.strip()]
        else:
            # Fallback to headers if not found in body
            details['attendees'] = [attendee.strip() for attendee in details.get('to', '').split(',') if attendee.strip()]

    return details

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    logging.info("get_meetings function called")  # Log when the function is called
    """Fetch and return meeting details from calendar invites."""
    service = authenticate_gmail()
    
    # Query for emails with .ics attachments
    query = 'has:attachment filename:ics'
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    logging.info(f"Found {len(messages)} messages with .ics attachments.")

    meeting_details = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['filename'].endswith('.ics'):
                    logging.info(f"Found .ics attachment: {part['filename']}")
                    ics_data = download_attachment(service, message['id'], part['body']['attachmentId'])
                    logging.info(f"Downloaded .ics data: {ics_data}")  # Log the raw .ics data
                    event_details = parse_ics(ics_data)  # Parse the .ics data
                    logging.info(f"Parsed event details: {event_details}")  # Log the parsed event details
                    meeting_details.append(event_details)

    return jsonify(meeting_details)

def download_attachment(service, message_id, attachment_id):
    """Download the attachment from the email."""
    attachment = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id).execute()
    return base64.urlsafe_b64decode(attachment['data']).decode('utf-8')  # Decode the base64 data

def parse_ics(ics_data):
    """Parse the .ics data and extract relevant event details."""
    calendar = Calendar.from_ical(ics_data)
    event_details = {}

    for component in calendar.walk():
        if component.name == "VEVENT":
            event_details['title'] = component.get('summary')  # Meeting title
            event_details['guests'] = [str(attendee) for attendee in component.get('attendee', [])]  # Guests
            
            # Check for the meeting link in the X-GOOGLE-CONFERENCE field
            event_details['link'] = component.get('X-GOOGLE-CONFERENCE') or None
            
            # If the link is still None, you can also check the description for the Google Meet link
            if not event_details['link']:
                description = component.get('description', '')
                match = re.search(r'https?://[^\s]+', description)
                if match:
                    event_details['link'] = match.group(0)  # Extract the first URL found in the description

            event_details['date'] = component.get('dtstart').dt.date().isoformat()  # Meeting date
            event_details['time'] = component.get('dtstart').dt.time().isoformat()  # Meeting time

    return event_details

if __name__ == '__main__':
    # Call the get_meetings function directly for testing
    with app.app_context():  # Create an application context
        meetings = get_meetings()  # Call the function
        print(meetings.get_json())  # Print the JSON response

    socketio.run(app, port=61372)
