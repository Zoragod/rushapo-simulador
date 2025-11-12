# Simulador Monte Carlo xG (Rushapo)

Simulador de resultados de fútbol basado en métricas de Expected Goals (xG) usando Monte Carlo. Incluye:
- Modelo Poisson con choques lognormales.
- Probabilidades de mercados: 1X2, Over/Under 2.5 y 3.5, BTTS, distribuciones de marcadores.
- Cálculo de cuotas justas y valor esperado (EV) al ingresar cuotas del bookmaker.
- Exportación a Excel (formateada si está `xlsxwriter`).
- Interfaz web mínima con Flask.

## Requisitos
Python 3.10+ (se probó con 3.13). Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecución local
Script standalone:
```bash
python simulador_rushapo.py
```
Servidor web (Flask):
```bash
python app.py
```
Abrir: http://localhost:5000

## Campos principales
- xGF/xGA Local/Visit: promedios de goles esperados a favor y en contra según condición.
- HFA: factor de ventaja local (>1 favorece al local).
- Sigma: volatilidad para choques multiplicativos.
- n_sims: número de simulaciones Monte Carlo.

## Cuotas y EV
Ingresa cuotas del book en el panel desplegable; la tabla mostrará:
- Prob (sim)
- Cuota justa (1/prob)
- Prob implícita (1/cuota_book)
- EV = prob_sim * cuota_book - 1 (verde si >0)

## Exportar a Excel
Se genera `Rushapo_Simulacion_Completa.xlsx` con hojas: Resumen, Marcadores, Sensibilidad, Cuotas & EV, Simulaciones.

## Despliegue en Render
1. Crea repositorio en GitHub.
2. Sube todos los archivos (incluye `render.yaml`).
3. En Render: New + Web Service + Conectar repo.
4. Render detectará Python y ejecutará:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
5. Una vez deploy, tendrás una URL pública.

## Despliegue en Railway (alternativa)
- Crea proyecto nuevo → Deploy from GitHub repo.
- Añade variable `PORT` si Railway lo requiere (gunicorn la usa automáticamente si se expone).
- Comando start: `gunicorn app:app --bind 0.0.0.0:$PORT`

## Variables de entorno (opcional)
Puedes parametrizar semilla, tamaño de simulaciones, etc. usando `os.getenv` en `app.py` o `simulador_rushapo.py`.

## Estructura
```
app.py                # Flask web app
simulador_rushapo.py  # Lógica de simulación
templates/index.html  # Plantilla principal
requirements.txt      # Dependencias
Procfile              # Comando para gunicorn (Heroku/Render/Railway)
render.yaml           # Configuración Render
README.md             # Este documento
```

## Próximas mejoras sugeridas
- Cache de resultados para parámetros repetidos.
- API REST (endpoint JSON para consumir desde otro frontend).
- Incluir gráfico de sensibilidad en la web (guardado como PNG).
- Test unitarios de funciones (Poisson lambda y EV).

## Licencia
Define una licencia (MIT recomendada) si planeas hacerlo público.
