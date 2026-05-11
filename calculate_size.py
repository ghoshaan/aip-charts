#!/usr/bin/env python3
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CHARTS_FOLDER_ID = '1DjkbZ9YMC5fS-zZvIpDiP9dCkUL120nK'

def authenticate_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def get_folder_size(service, folder_id):
    total_size = 0
    file_count = 0
    
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token
        ).execute()

        for file in results.get('files', []):
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                # Recurse into subfolders
                size, count = get_folder_size(service, file['id'])
                total_size += size
                file_count += count
            else:
                size = int(file.get('size', 0))
                total_size += size
                file_count += 1
                
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    return total_size, file_count

def main():
    service = authenticate_drive()
    print(f"Scanning folder: {CHARTS_FOLDER_ID}...")
    total_bytes, total_files = get_folder_size(service, CHARTS_FOLDER_ID)
    
    mb = total_bytes / (1024 * 1024)
    gb = mb / 1024
    
    print("\n" + "="*30)
    print(f"Total Files: {total_files}")
    print(f"Total Size:  {mb:.2f} MB ({gb:.2f} GB)")
    print("="*30)

if __name__ == '__main__':
    main()
