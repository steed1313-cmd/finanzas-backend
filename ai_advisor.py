import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def parse_ai_error(error_str, is_fallback=False):
    """Parsea el error de Google y devuelve un mensaje amigable para el usuario."""
    error_str = str(error_str)
    
    if "429" in error_str or "Quota exceeded" in error_str:
        # Extraer los segundos si existen
        match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', error_str)
        secs = match.group(1) if match else "unos"
        
        if not is_fallback:
            return None # Señal para intentar con la clave 2
            
        return (f"⚠️ **Ambas Inteligencias Artificiales han superado su límite gratuito diario.**\n\n"
                f"Por favor, inténtalo de nuevo en **{secs} segundos** o cuando se restaure la cuota mañana.")
    
    return f"⚠️ Ocurrió un error al consultar la IA: {error_str}"

def call_gemini_with_fallback(prompt):
    """Intenta llamar a Gemini con la primera clave, y si falla por cuota, usa la segunda."""
    api_key_1 = os.getenv("GEMINI_API_KEY")
    api_key_2 = os.getenv("GEMINI_API_KEY_2")
    
    if not api_key_1 and not api_key_2:
        return "⚠️ Error: Las claves API no están configuradas en el servidor."

    model_name = 'gemini-flash-lite-latest'

    # Intento 1
    if api_key_1:
        try:
            genai.configure(api_key=api_key_1)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception as e:
            parsed = parse_ai_error(e, is_fallback=False)
            if parsed is not None:
                return parsed # Es un error distinto a cuota, retornar
            # Si parsed es None, falló por cuota, intentar con key 2 si existe
            if not api_key_2:
                return parse_ai_error(e, is_fallback=True)

    # Intento 2 (Fallback)
    if api_key_2:
        try:
            genai.configure(api_key=api_key_2)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception as e:
            return parse_ai_error(e, is_fallback=True)

def get_ai_debt_plan(deudas):
    """Genera un plan estratégico de pago de deudas."""
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
    return call_gemini_with_fallback(prompt)

def get_ai_expense_audit(gastos_mensuales):
    """Genera una auditoría de gastos mensuales."""
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
    return call_gemini_with_fallback(prompt)
