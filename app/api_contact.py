# app/api_contact.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
import os, smtplib, ssl
from email.message import EmailMessage
from email.header import Header
from starlette.concurrency import run_in_threadpool

# ===== מודל קלט מהטופס =====
class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)

app = FastAPI(title="Contact API")

# ===== שליחה סינכרונית (תרוץ ב-threadpool) =====
def send_email_sync(
    subject: str,
    body_text: str,
    mail_to: str,
    mail_from: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    use_tls: bool = True,
    reply_to: str | None = None,
) -> None:
    msg = EmailMessage()
    # כותרת בעברית (UTF-8)
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = mail_from
    msg["To"] = mail_to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["X-Mailer"] = "BusoftSite/1.0"

    # גוף המייל כ־UTF-8 (טקסט רגיל)
    msg.set_content(body_text, subtype="plain", charset="utf-8")

    # חיבור ושליחה
    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as s:
        if use_tls:
            context = ssl.create_default_context()
            s.starttls(context=context)
        if smtp_user and smtp_password:
            s.login(smtp_user, smtp_password)
        s.send_message(msg)

# ===== נקודת הקצה שהאתר קורא אליה (/api/contact) =====
@app.post("/contact")
async def contact(payload: ContactIn):
    # ENV (מוגדרים ב-docker compose / Render)
    MAIL_TO = os.getenv("MAIL_TO", "uri@busoft.co.il")           # נמען סופי
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@busoft.co.il")  # חייב להיות Sender מאומת ב-SendGrid
    SMTP_HOST = os.getenv("SMTP_HOST")                           # חובה כששולחים באמת
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")                           # SendGrid: "apikey"
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")                   # SendGrid: SG.xxxxx
    DRY_RUN = os.getenv("DRY_RUN", "0")                          # "1" = מצב אימון (לא שולח, רק לוג)

    subject = f"פניית צור קשר מהאתר – {payload.name}"
    body = (
        f"שם: {payload.name}\n"
        f"אימייל: {payload.email}\n\n"
        f"הודעה:\n{payload.message}\n"
    )

    # מצב אימון / חוסר הגדרות SMTP → לא שולחים באמת
    if DRY_RUN == "1" or not SMTP_HOST:
        print("--- DRY RUN / DEBUG ---")
        print("To:", MAIL_TO)
        print("From:", MAIL_FROM)
        print("Subject:", subject)
        print(body)
        return {"ok": True, "debug": True}

    try:
        await run_in_threadpool(
            send_email_sync,
            subject,
            body,
            MAIL_TO,
            MAIL_FROM,
            SMTP_HOST,
            SMTP_PORT,
            SMTP_USER,
            SMTP_PASSWORD,
            True,                 # use_tls
            payload.email,        # Reply-To = מי שמילא את הטופס
        )
        return {"ok": True}
    except Exception as e:
        # נעביר החוצה שגיאת SMTP מובנת (כולל 550 אם Sender לא מאומת)
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")
