from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List
import os
from dotenv import load_dotenv

from . import models, schemas, database
from .database import engine

# Load env variables
from pathlib import Path
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS") == "True",
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS") == "True",
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS") == "True"
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/email")
async def send_email(email: schemas.EmailSchema, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Log to DB
    db_log = models.EmailLog(
        email_destinataire=email.email_destinataire,
        message=email.message
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    # Send Real Email
    message = MessageSchema(
        subject="Notification Nouvelle Commande",
        recipients=[email.email_destinataire],
        body=email.message,
        subtype=MessageType.plain
    )
    
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    
    return {"status": "success", "message": "Email sending queued and logged"}

@app.get("/logs")
async def get_logs(db: Session = Depends(get_db)):
    return db.query(models.EmailLog).all()
