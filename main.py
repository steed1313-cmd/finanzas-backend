from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Dict, Any
import json
import database, models, schemas, auth
import ai_advisor

models.Base.metadata.create_all(bind=database.engine)

# Auto-migrate SQLite if columns don't exist
def add_column_if_not_exists(col_def):
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_def}"))
            conn.commit()
    except Exception:
        pass

add_column_if_not_exists("expiration_date VARCHAR")
add_column_if_not_exists("last_payment_date VARCHAR")
add_column_if_not_exists("subscription_type VARCHAR DEFAULT 'GRATUITO'")
add_column_if_not_exists("is_suspended INTEGER DEFAULT 0")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from datetime import datetime, timedelta

    user = db.query(models.User).filter(func.lower(models.User.username) == func.lower(form_data.username)).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Cuenta suspendida por el administrador.")
        
    if user.subscription_type != "VITALICIO" and user.expiration_date:
        # Check if expired
        try:
            exp_date = datetime.fromisoformat(user.expiration_date)
            if datetime.now() > exp_date:
                raise HTTPException(status_code=403, detail="Suscripción vencida. Por favor, renueva tu pago.")
        except ValueError:
            pass # Ignore parsing errors just in case
            
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/api/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/api/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from datetime import datetime, timedelta
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 30 days free trial by default
    trial_end = (datetime.now() + timedelta(days=30)).isoformat()
    
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username, 
        hashed_password=hashed_password,
        role=user.role,
        forex_enabled=user.forex_enabled,
        subscription_type="GRATUITO",
        expiration_date=trial_end
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/users/{user_id}/subscription", response_model=schemas.User)
def update_user_subscription(
    user_id: int, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
        
    if "is_suspended" in payload:
        user_to_update.is_suspended = int(payload["is_suspended"])
    if "subscription_type" in payload:
        user_to_update.subscription_type = payload["subscription_type"]
    if "expiration_date" in payload:
        user_to_update.expiration_date = payload["expiration_date"]
    if "last_payment_date" in payload:
        user_to_update.last_payment_date = payload["last_payment_date"]
        
    db.commit()
    db.refresh(user_to_update)
    return user_to_update

@app.put("/api/users/{username}/password")
def update_user_password(username: str, data: schemas.UserUpdatePassword, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.hashed_password = auth.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@app.put("/api/users/{username}/forex")
def update_user_forex(username: str, data: schemas.UserUpdateForex, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.forex_enabled = data.forex_enabled
    db.commit()
    return {"message": "Forex permission updated successfully"}

@app.delete("/api/users/{username}")
def delete_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
        
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete associated data
    db.query(models.MonthlyData).filter(models.MonthlyData.user_id == db_user.id).delete()
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/api/users", response_model=List[schemas.User])
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return db.query(models.User).all()

@app.get("/api/data/{month_key}")
def get_monthly_data(month_key: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_data = db.query(models.MonthlyData).filter(
        models.MonthlyData.user_id == current_user.id,
        models.MonthlyData.month_key == month_key
    ).first()
    
    if db_data:
        return json.loads(db_data.data)
    
    # Return empty structure if not found
    return {
        "ingresos": [],
        "facturas": [],
        "gastos": [],
        "seguimiento": [],
        "deudasMensual": [],
        "ahorros": []
    }

@app.post("/api/data/{month_key}")
def save_monthly_data(month_key: str, payload: Dict[Any, Any], db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_data = db.query(models.MonthlyData).filter(
        models.MonthlyData.user_id == current_user.id,
        models.MonthlyData.month_key == month_key
    ).first()
    
    data_str = json.dumps(payload)
    
    if db_data:
        db_data.data = data_str
    else:
        db_data = models.MonthlyData(user_id=current_user.id, month_key=month_key, data=data_str)
        db.add(db_data)
        
    db.commit()
    return {"message": "Data saved successfully"}

@app.post("/api/data/prestamos")
def update_prestamos_data(data: dict, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    json_str = json.dumps(data)
    record = db.query(models.MonthlyData).filter(
        models.MonthlyData.user_id == current_user.id,
        models.MonthlyData.month_key == "prestamos"
    ).first()
    if record:
        record.data = json_str
    else:
        record = models.MonthlyData(user_id=current_user.id, month_key="prestamos", data=json_str)
        db.add(record)
    db.commit()
    return {"status": "ok"}

# --- AI ADVISOR ENDPOINTS ---

@app.post("/api/ai/advisor/deudas")
def get_debt_advice(deudas: List[Dict[str, Any]], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_debt_plan(deudas)
    return {"advice": advice}

@app.post("/api/ai/advisor/gastos")
def get_expense_advice(gastos: Dict[str, Any], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_expense_audit(gastos)
    return {"advice": advice}

@app.post("/api/ai/advisor/wealth")
def get_wealth_advice(data: Dict[str, Any], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_wealth_plan(data.get("ahorros", []), data.get("ingresos", []))
    return {"advice": advice}

@app.post("/api/ai/advisor/predictive")
def get_predictive_advice(data: Dict[str, Any], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_predictive_analysis(data.get("historial", []))
    return {"advice": advice}

@app.post("/api/ai/advisor/simulator")
def get_simulator_advice(data: Dict[str, Any], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_scenario_simulator(data.get("finanzas", {}), data.get("escenario", ""))
    return {"advice": advice}

@app.post("/api/ai/advisor/annual")
def get_annual_advice(data: Dict[str, Any], current_user: models.User = Depends(auth.get_current_user)):
    advice = ai_advisor.get_ai_annual_auditor(data)
    return {"advice": advice}

@app.get("/api/export")
def export_user_data(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    records = db.query(models.MonthlyData).filter(models.MonthlyData.user_id == current_user.id).all()
    export_data = {}
    for r in records:
        try:
            export_data[r.month_key] = json.loads(r.data)
        except:
            pass
    return export_data

@app.post("/api/migrate")
def migrate_data(payload: schemas.MigrateData, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # payload.local_storage_data is the whole db from localStorage
    # Loop through the keys (e.g. "Julio-2026") and save them
    local_data = payload.local_storage_data
    for month_key, month_data in local_data.items():
        data_str = json.dumps(month_data)
        db_data = db.query(models.MonthlyData).filter(
            models.MonthlyData.user_id == current_user.id,
            models.MonthlyData.month_key == month_key
        ).first()
        
        if db_data:
            db_data.data = data_str
        else:
            db_data = models.MonthlyData(user_id=current_user.id, month_key=month_key, data=data_str)
            db.add(db_data)
            
    db.commit()
    return {"message": "Migration completed successfully"}

# Initialize default admin user if it doesn't exist
@app.on_event("startup")
def create_default_admin():
    # Auto-migration to add forex_enabled column if it doesn't exist
    try:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN forex_enabled INTEGER DEFAULT 0"))
        print("Migrated database: added forex_enabled column")
    except Exception as e:
        print("Column forex_enabled already exists or error:", str(e))

    db = database.SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed_password = auth.get_password_hash("admin123")
        admin = models.User(username="admin", hashed_password=hashed_password, role="ADMIN")
        db.add(admin)
        db.commit()
    db.close()
