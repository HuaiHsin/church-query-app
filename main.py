from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from drive_utils import download_file_from_drive
import pandas as pd
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, year: int = None, month: int = None, name: str = None):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "year": year,
        "month": month,
        "name": name,
        "results": None,
        "error": None
    })


@app.get("/query", response_class=HTMLResponse)
async def query_schedule(request: Request, year: int, month: int, name: str):
    folder_id = "18onzzoBnI3Lhwfm8IlMhwrOoIrcV5g8J"
    minguo_year = year - 1911
    month_name = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"][month - 1]
    search_keywords = [f"{minguo_year}年", f"{month_name}", "聖工安排"]

    filepath, ext = download_file_from_drive(folder_id, search_keywords)
    if not filepath:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "year": year,
            "month": month,
            "name": name,
            "results": None,
            "error": f"找不到檔案：{' + '.join(search_keywords)}"
        })

    try:
        df = pd.read_csv(filepath, header=1) if ext == '.csv' else pd.read_excel(filepath, header=1)
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "year": year,
            "month": month,
            "name": name,
            "results": None,
            "error": f"讀取檔案時錯誤：{str(e)}"
        })

    df.columns = [c.strip() for c in df.columns]

    # 補合併儲存格造成的空值
    for i in range(1, len(df)):
        if pd.isna(df.at[i, '日期']) and pd.notna(df.at[i-1, '日期']):
            df.at[i, '日期'] = df.at[i-1, '日期']
            df.at[i, '星期'] = df.at[i-1, '星期']
            df.at[i, '地區'] = df.at[i-1, '地區']

    result = []
    name_fields = ['領 會', '翻 譯', '唱 詩', '司 琴', '音 控', '投影操作', '岡山車載', '路竹車載']
    misc_field = '訪問/炊事/謝飯/跪墊/附記'

    prev_date = None

    for _, row in df.iterrows():
        try:
            day = int(float(row['日期']))
        except:
            continue

        date_str = f"{year}/{month:02d}/{day:02d}"
        weekday = str(row['星期']).strip()
        is_saturday = weekday == '六'
        is_second_row = prev_date == row['日期'] and is_saturday

        if is_saturday:
            if is_second_row:
                start_time = f"{date_str}T13:30:00+08:00"
                end_time = f"{date_str}T15:00:00+08:00"
                time_range = "13:30-15:00"
            else:
                start_time = f"{date_str}T09:30:00+08:00"
                end_time = f"{date_str}T11:00:00+08:00"
                time_range = "09:30-11:00"
        else:
            start_time = f"{date_str}T20:00:00+08:00"
            end_time = f"{date_str}T21:00:00+08:00"
            time_range = "20:00-21:00"

        matched = []

        for field in name_fields:
            if field in row and pd.notna(row[field]):
                cell_value = str(row[field])
                if name in cell_value:
                    matched.append(f"{field}: {cell_value}")

        if misc_field in row and pd.notna(row[misc_field]):
            misc_value = str(row[misc_field])
            if name in misc_value:
                matched.append(misc_value)

        if matched:
            result.append({
                "date": date_str,
                "weekday": weekday,
                "tasks": matched,
                "time": time_range
            })

        prev_date = row['日期']

    return templates.TemplateResponse("index.html", {
        "request": request,
        "year": year,
        "month": month,
        "name": name,
        "results": result,
        "error": None
    })
