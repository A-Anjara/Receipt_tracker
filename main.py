from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from datetime import date
import sqlite3
import io
from PIL import Image
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from PIL import Image, ImageEnhance, ImageOps
import requests
import json
import base64
from io import BytesIO
import re
from datetime import datetime , timedelta, timezone, date
from utils import *

app = FastAPI()
app.mount("/static",StaticFiles(directory="documents"),name="static")
class DateTime(BaseModel):
    date_start: date
    date_end: date

@app.get('/',response_class=FileResponse)
async def home():
    return FileResponse("static/dashboard.html")

@app.post('/filter')
def filter(datee:DateTime):
    with sqlite3.connect("db.sql") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(f"SELECT id,title,total,date,type,file FROM RECEIPTS WHERE date(date) BETWEEN ? AND ?",(datee.date_start.isoformat(),datee.date_end.isoformat()))
        data = cur.fetchall()
    data = [dict(row) for row in data]
    return {"results": data}

@app.post('/upload')
def upload(file: UploadFile):
    image_bytes = file.file.read()
    image = Image.open(io.BytesIO(image_bytes))
    value = process_file(image,file.filename)
    if(value):
        return {"message":"success"}
    
    else:
        return {"message":"fail"}
