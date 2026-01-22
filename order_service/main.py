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

# Redis Connection
import redis
import os
import json

redis_host = os.getenv("REDIS_HOST", "redis-service")
rd = redis.Redis(host=redis_host, port=6379, db=0)



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

    # Cache Logic
    if rd.exists("orders_cache"):
        print("Cache Hit! Serving from Redis.")
        orders_data = json.loads(rd.get("orders_cache"))
        # Reconstruct objects from dicts/json if needed for template, 
        # but models.Order is an object. 
        # For simplicity, we might just pass the list of dicts if the template supports it,
        # OR we need to be careful with serialization.
        # Assuming the template uses dot access, we might need a simple wrapper or just pass dicts 
        # (Jinja2 handles dicts/objects often, but dot notation implies objects).
        # To be safe with existing template that likely uses order.id, etc., 
        # let's assume we store list of dicts and the template can handle it or we convert back.
        # However, SQLAlchemy objects are not directly JSON serializable. 
        # We need a serializer.
        orders = orders_data # Passing dicts to template usually works if template uses dot notation and we convert or if template uses item lookup. 
        # Standard Jinja2: {{ order.id }} works for dicts too in many contexts if configured, 
        # but default is object.attribute. Dicts use order['id']. 
        # To avoid breaking template, let's create a dynamic object or ensure serialization compatibility.
        # ACTUALLY: Let's fetch from DB, serialize to DICT for cache, 
        # and when reading from cache, ensure template can read it.
        # Re-querying is safer if we want full objects, but defeats the cache purpose.
        # Let's trust that we can pass a list of dicts/objects that act like objects.
        # A simple hack:
        class OrderItem:
            def __init__(self, **entries):
                self.__dict__.update(entries)
        orders = [OrderItem(**o) for o in orders_data]
    else:
        print("Cache Miss! Fetching from DB.")
        orders = db.query(models.Order).all()
        # Serialize for Redis
        orders_data = []
        for o in orders:
            orders_data.append({
                "id": o.id,
                "product": o.product,
                "quantity": o.quantity,
                "price": o.price,
                "status": o.status,
                "email_client": o.email_client
            })
        rd.setex("orders_cache", 30, json.dumps(orders_data))

    return templates.TemplateResponse("dashboard.html", {"request": request, "orders": orders, "user_email": user_email})

@app.post("/create_order")
async def create_order(request: Request, product: str = Form(...), quantity: int = Form(...), price: float = Form(...), db: Session = Depends(get_db)):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")
        
    new_order = models.Order(
        product=product,
        quantity=quantity,
        price=price,
        status="Pending",
        email_client=user_email
    )
    db.add(new_order)
    db.commit()
    
    # Invalidate Cache
    rd.delete("orders_cache")
    print("New Order created. Cache invalidated.")
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/sent", response_class=HTMLResponse)
async def sent_page(request: Request):
    user_email = request.session.get("user_email")
    if not user_email:
        return RedirectResponse(url="/login")

    # Call Notification Service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://notification-service/email",
                json={
                    "email_destinataire": user_email,
                    "message": f"Confirmation de votre commande. Merci {user_email} !"
                }
            )
            print(f"Notification Service Response: {response.status_code}")
    except Exception as e:
        print(f"Error calling Notification Service: {e}")

    return templates.TemplateResponse("sent.html", {"request": request})
