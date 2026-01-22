from fastapi import FastAPI, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from . import models, database
from .database import engine
import httpx

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(SessionMiddleware, secret_key="Abj20123AQlQ")

# Templates
templates = Jinja2Templates(directory="order_service/templates")

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...)):
    request.session["user_email"] = email
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, db: Session = Depends(get_db)):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
        
    orders = db.query(models.Order).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "orders": orders, "user_email": user_email})

@app.get("/sent", response_class=HTMLResponse)
async def sent_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")

    # Call Notification Service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8001/email",
                json={
                    "email_destinataire": user_email,
                    "message": f"Confirmation de votre commande. Merci {user_email} !"
                }
            )
            print(f"Notification Service Response: {response.status_code}")
    except Exception as e:
        print(f"Error calling Notification Service: {e}")

    return templates.TemplateResponse("sent.html", {"request": request})
