from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db, Contact
from .schemas import ContactCreate

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Busoft")

# מיפוי סטטי: /assets → app/static/assets
assets_dir = BASE_DIR / "static" / "assets"
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# תבניות
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# יצירת טבלאות (אם לא קיימות)
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/contact")
def contact(form: ContactCreate, db: Session = Depends(get_db)):
    row = Contact(name=form.name, email=form.email, message=form.message)
    db.add(row)
    db.commit()
    return {"ok": True, "id": row.id}

@app.get("/health")
def health():
    return {"ok": True}
