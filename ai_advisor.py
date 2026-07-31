import os
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_ai_debt_plan(deudas):
    """
    Genera un plan estratégico de pago de deudas.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        keys = ", ".join(os.environ.keys())
        return f"⚠️ Error: La clave API no está configurada en Render. Variables detectadas en el servidor: {keys}"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    Eres un asesor financiero patrimonial experto (nivel institucional). 
    El usuario te envía su lista de deudas actuales y quiere un Plan de Aceleración Inteligente.
    Tu objetivo es analizar la situación y recomendar la mejor estrategia (Avalancha o Bola de Nieve) de manera clara, profesional, y altamente motivadora.
    Usa formato Markdown con encabezados, negritas y listas. NO saludes como un robot, entra directo al análisis.
    
    Datos de las deudas del usuario:
    {deudas}
    
    Por favor, responde estructurando:
    1. Diagnóstico breve de la situación.
    2. La deuda más tóxica a atacar inmediatamente y por qué.
    3. Plan de acción paso a paso.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model_list = ", ".join(available)
            return f"⚠️ Error de modelo. Modelos en tu cuenta: {model_list}. Error original: {e}"
        except Exception as e2:
            return f"⚠️ Ocurrió un error al auditar las deudas: {e}"

def get_ai_expense_audit(gastos_mensuales):
    """
    Genera una auditoría de gastos mensuales.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        keys = ", ".join(os.environ.keys())
        return f"⚠️ Error: La clave API no está configurada en Render. Variables detectadas en el servidor: {keys}"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    Eres un auditor financiero experto. El usuario quiere que audites sus gastos de este mes para encontrar fugas de dinero (gastos hormiga) y optimizar su presupuesto.
    Responde de forma ejecutiva, usando formato Markdown (encabezados, listas, negritas) de forma clara y directa.
    
    Datos financieros del usuario este mes:
    {gastos_mensuales}
    
    Responde estructurando:
    1. Análisis de liquidez general (Ingresos vs Gastos).
    2. Detección de "Puntos de Fuga" o áreas donde está gastando de más.
    3. 3 recomendaciones prácticas para optimizar el presupuesto del próximo mes.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model_list = ", ".join(available)
            return f"⚠️ Error de modelo. Modelos en tu cuenta: {model_list}. Error original: {e}"
        except Exception as e2:
            return f"⚠️ Ocurrió un error al auditar los gastos: {e}"
