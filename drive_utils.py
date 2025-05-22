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


def ensure_cache_dir():
    os.makedirs("cache", exist_ok=True)


def download_file_from_drive(folder_id, keywords, ext_list=['.csv', '.xlsx']):
    service = get_drive_service()
    ensure_cache_dir()

    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    for ext in ext_list:
        for file in files:
            name = file['name']
            if all(k in name for k in keywords) and name.endswith(ext):
                file_id = file['id']
                cache_path = os.path.join("cache", name)
                if os.path.exists(cache_path):
                    return cache_path, ext

                # 下載
                request = service.files().get_media(fileId=file_id)
                with open(cache_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                return cache_path, ext

    return None, None


def extract_choir_schedule_from_image(folder_id, keywords, target_month, target_name, return_debug=False):
    service = get_drive_service()
    ensure_cache_dir()

    query = f"'{folder_id}' in parents and mimeType='image/jpeg'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    for file in files:
        name = file['name']
        if all(k in name for k in keywords):
            file_id = file['id']
            img_path = os.path.join("cache", name)
            ocr_txt_path = img_path + ".txt"

            used_cache = False

            if os.path.exists(ocr_txt_path):
                with open(ocr_txt_path, encoding='utf-8') as f:
                    text = f.read()
                used_cache = True
            else:
                if not os.path.exists(img_path):
                    request = service.files().get_media(fileId=file_id)
                    with open(img_path, 'wb') as f:
                        downloader = MediaIoBaseDownload(f, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()

                img = Image.open(img_path)
                text = pytesseract.image_to_string(img, lang='chi_tra')

                with open(ocr_txt_path, "w", encoding="utf-8") as f:
                    f.write(text)

            result_lines = parse_schedule_text(text, target_month, target_name)

            if return_debug:
                return result_lines, text, used_cache
            else:
                return result_lines

    if return_debug:
        return [], "", False
    return []

def parse_schedule_text(text, month, name):
    lines = text.splitlines()
    results = []
    current_date = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1. 尋找日期（例如 6月7 或 6月14）
        date_match = re.search(rf"{month}月\d{{1,2}}", line)
        if date_match:
            current_date = date_match.group()

        # 2. 找到名稱（模糊比對，例如「雅婷」）
        if name in line and current_date:
            results.append(f"{current_date}：{line}")

    return results
