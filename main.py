from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from drive_utils import (
    download_file_from_drive,
    extract_choir_schedule_from_image,
    parse_choir_text_structured
)
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, year: int = None, month: int = None, name: str = None):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "year": year,
        "month": month,
        "name": name,
        "unified_results": None,
        "ocr_debug": None,
        "ocr_from_cache": False,
        "error": None
    })


@app.get("/query", response_class=HTMLResponse)
async def query_schedule(request: Request, year: int, month: int, name: str):
    folder_id = "18onzzoBnI3Lhwfm8IlMhwrOoIrcV5g8J"
    minguo_year = year - 1911
    month_name = ["一月", "二月", "三月", "四月", "五月", "六月",
                  "七月", "八月", "九月", "十月", "十一月", "十二月"][month - 1]
    search_keywords = [f"{minguo_year}年", month_name, "聖工安排"]

    filepath, ext = download_file_from_drive(folder_id, search_keywords)
    unified_results = []
    error = None

    # --- 表格處理（CSV/XLSX） ---
    if filepath:
        try:
            df = pd.read_csv(filepath, header=1) if ext == '.csv' else pd.read_excel(filepath, header=1)
            df.columns = [c.strip() for c in df.columns]

            for i in range(1, len(df)):
                if pd.isna(df.at[i, '日期']) and pd.notna(df.at[i-1, '日期']):
                    df.at[i, '日期'] = df.at[i-1, '日期']
                    df.at[i, '星期'] = df.at[i-1, '星期']
                    df.at[i, '地區'] = df.at[i-1, '地區']

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
                    time_range = "13:30-15:00" if is_second_row else "09:30-11:00"
                else:
                    time_range = "20:00-21:00"

                for field in name_fields:
                    if field in row and pd.notna(row[field]):
                        cell = str(row[field])
                        if name in cell:
                            unified_results.append({
                                "date": date_str,
                                "time": time_range,
                                "role": field,
                                "name": cell,
                                "source": "表格"
                            })
                if misc_field in row and pd.notna(row[misc_field]):
                    misc_val = str(row[misc_field])
                    if name in misc_val:
                        unified_results.append({
                            "date": date_str,
                            "time": time_range,
                            "role": "附記",
                            "name": misc_val,
                            "source": "表格"
                        })

                prev_date = row['日期']
        except Exception as e:
            error = f"CSV/XLSX 讀取錯誤：{str(e)}"

    # --- 圖片 OCR 處理 ---
    choir_keywords = [f"{minguo_year}年", "佳音", "安排"]
    _, ocr_text, ocr_from_cache = extract_choir_schedule_from_image(
        folder_id, choir_keywords, month, name, return_debug=True
    )

    choir_results = parse_choir_text_structured(ocr_text, month, name)
    for r in choir_results:
        unified_results.append({
            "date": r["date"],
            "time": r["time"],
            "role": r["role"],
            "name": r["name"],
            "source": "圖片"
        })

    unified_results.sort(key=lambda x: x["date"] + x["time"])

    return templates.TemplateResponse("index.html", {
        "request": request,
        "year": year,
        "month": month,
        "name": name,
        "unified_results": unified_results,
        "ocr_debug": ocr_text,
        "ocr_from_cache": ocr_from_cache,
        "error": error
    })
