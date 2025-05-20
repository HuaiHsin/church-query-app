from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from drive_utils import download_csv_from_drive
import pandas as pd
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/query", response_class=HTMLResponse)
async def query_schedule(request: Request, year: int, month: int, name: str):
    folder_id = "18onzzoBnI3Lhwfm8IlMhwrOoIrcV5g8J"
    minguo_year = year - 1911
    month_name = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"][month - 1]
    target_filename = f"{minguo_year}年{month_name}聖工安排表.csv"

    filepath = download_csv_from_drive(folder_id, target_filename)
    if not filepath:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"找不到檔案：{target_filename}"
        })

    df = pd.read_csv(filepath, header=1)
    df.columns = [c.strip() for c in df.columns]
    for i in range(1, len(df)):
        if pd.isna(df.at[i, '日期']) and pd.notna(df.at[i-1, '日期']):
            df.at[i, '日期'] = df.at[i-1, '日期']
            df.at[i, '星期'] = df.at[i-1, '星期']
            df.at[i, '地區'] = df.at[i-1, '地區']

    result = []
    name_fields = ['領 會', '翻 譯', '唱 詩', '司 琴', '音 控', '投影操作', '岡山車載', '路竹車載']
    misc_field = '訪問/炊事/謝飯/跪墊/附記'

    for _, row in df.iterrows():
        try:
            day = int(float(row['日期']))
        except:
            continue

        date_str = f"{year}/{month:02d}/{day:02d}"
        time_range = "20:00" if row['星期'] != '六' else "09:30"
        matched = []

        for field in name_fields:
            if field in row and pd.notna(row[field]) and name in str(row[field]):
                matched.append(f"{field}: {row[field]}")

        if misc_field in row and pd.notna(row[misc_field]) and name in str(row[misc_field]):
            matched.append(row[misc_field])

        if matched:
            result.append({
                "date": date_str,
                "weekday": row['星期'],
                "tasks": matched,
                "time": time_range
            })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": result,
        "name": name,
        "year": year,
        "month": month
    })
