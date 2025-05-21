from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'service_account.json'

def download_file_from_drive(folder_id, target_filename_keywords):
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=creds)

    response = service.files().list(
        q=f"'{folder_id}' in parents and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')",
        spaces='drive',
        fields='files(id, name, mimeType)'
    ).execute()

    files = response.get('files', [])
    match = next((f for f in files if all(kw in f['name'] for kw in target_filename_keywords)), None)
    if not match:
        return None, None  # 沒找到

    file_id = match['id']
    file_name = match['name']
    mime_type = match['mimeType']
    ext = '.csv' if mime_type == 'text/csv' else '.xlsx'

    filepath = f"temp_{file_name}"
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(filepath, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return filepath, ext
