import os
import io
import re
import pytesseract
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'service_account.json'


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def download_file_from_drive(folder_id, keywords, ext_list=['.csv', '.xlsx']):
    service = get_drive_service()
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    for ext in ext_list:
        for file in files:
            name = file['name']
            if all(k in name for k in keywords) and name.endswith(ext):
                file_id = file['id']
                request = service.files().get_media(fileId=file_id)
                file_path = f"temp_download{ext}"
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                return file_path, ext
    return None, None


def extract_choir_schedule_from_image(folder_id, keywords, target_month, target_name):
    service = get_drive_service()
    query = f"'{folder_id}' in parents and mimeType='image/jpeg'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    for file in files:
        name = file['name']
        if all(k in name for k in keywords):
            file_id = file['id']
            request = service.files().get_media(fileId=file_id)
            img_path = "choir_temp.jpg"
            with open(img_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            img = Image.open(img_path)
            text = pytesseract.image_to_string(img, lang='chi_tra')

            return parse_schedule_text(text, target_month, target_name)
    return []


def parse_schedule_text(text, month, name):
    lines = text.splitlines()
    results = []
    current_date = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 判斷是否為新日期行（例如 6月7日）
        if re.search(rf"{month}月\d{{1,2}}日", line):
            current_date = re.search(rf"{month}月\d{{1,2}}日", line).group()

        # 如果這行包含查詢名稱，就視為有效任務
        if name in line and current_date:
            results.append(f"{current_date}：{line}")

    return results
