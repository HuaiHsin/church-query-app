from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

def download_csv_from_drive(folder_id, target_filename):
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # 列出資料夾內所有檔案
    response = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='text/csv'",
        spaces='drive',
        fields='files(id, name)'
    ).execute()

    files = response.get('files', [])
    match = next((f for f in files if target_filename in f['name']), None)
    if not match:
        return None

    request = service.files().get_media(fileId=match['id'])
    filepath = f"temp_{match['name']}"
    fh = io.FileIO(filepath, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    return filepath
