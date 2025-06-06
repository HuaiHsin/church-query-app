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

NAME_CORRECTIONS = {
    "請雅": "靖雅",
    "風羚": "俐羚",
    "亞短": "亞箴",
    "逝勒": "迦勒",
    "迴勒": "迦勒"
}

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
                request = service.files().get_media(fileId=file_id)
                with open(cache_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                return cache_path, ext
    return None, None

def correct_ocr_errors(line):
    for wrong, correct in NAME_CORRECTIONS.items():
        line = line.replace(wrong, correct)
    return line

def parse_schedule_text(text, target_month, name):
    lines = text.splitlines()
    results = []
    current_date = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = correct_ocr_errors(line)

        date_match = re.search(rf"{target_month}月\d{{1,2}}", line)
        if date_match:
            current_date = date_match.group()
        elif re.search(r"\d{1,2}月\d{1,2}", line):
            other_month_match = re.search(r"(\d{1,2})月\d{1,2}", line)
            if other_month_match and int(other_month_match.group(1)) != target_month:
                current_date = None

        if current_date and name in line:
            results.append(f"{current_date}：{line}")

    return results

def parse_choir_text_structured(text, target_month: int, target_name: str):
    lines = text.splitlines()
    results = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = correct_ocr_errors(line)

        # 確認是該月份資料行
        match = re.search(rf"{target_month}月\d{{1,2}}", line)
        if not match:
            continue

        date_str = match.group()
        date_parts = re.findall(r"(\d{1,2})月(\d{1,2})", date_str)
        if not date_parts:
            continue

        # 擷取人名群組
        content = line.replace(date_str, "").strip()
        content = re.sub(r"\d{2}:\d{2}.*", "", content)

        # 假設格式：教唱 / 司琴 / 分享 三組人名，用分隔符（多空格、制表符）或中文標點分段
        parts = re.split(r'\s{2,}|\t|　', content)
        parts = [p.strip() for p in parts if p.strip()]
        roles = ["教唱", "司琴", "分享"]

        for i in range(min(len(parts), 3)):
            for person in parts[i].replace(" ", "").split("/"):
                if target_name in person:
                    results.append({
                        "date": f"2025/{target_month:02d}/{date_parts[0][1]:0>2}",
                        "time": "16:30-18:00",
                        "role": roles[i],
                        "name": person
                    })

    return results

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

            if return_debug:
                return [], text, used_cache
            else:
                return []

    return ([], "", False) if return_debug else []
