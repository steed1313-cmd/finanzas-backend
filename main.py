from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Dict, Any
import json
import database, models, schemas, auth

models.Base.metadata.create_all(bind=database.engine)

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
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/api/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/api/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password, role="USER")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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
    db = database.SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed_password = auth.get_password_hash("admin123")
        admin = models.User(username="admin", hashed_password=hashed_password, role="ADMIN")
        db.add(admin)
        db.commit()
    db.close()
