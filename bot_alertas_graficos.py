import ccxt
import pandas as pd
import time
import matplotlib.pyplot as plt
from telegram import Bot
from io import BytesIO

# ===== CONFIGURACIÓN =====
API_TOKEN = "7901741145:AAFPr0wLmKVDkHV30_clU9eGcX8doi8mjQQ"
CHAT_ID = "1347933429"
INTERVALO = "15m"
CICLO = 300  # segundos entre revisiones

CRIPTO_PARES = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "TON/USDT", "TRX/USDT", "AVAX/USDT"
]

bot = Bot(token=API_TOKEN)
exchange = ccxt.binance()

# ===== FUNCIONES =====
def obtener_datos(par, intervalo, limite=100):
    velas = exchange.fetch_ohlcv(par, timeframe=intervalo, limit=limite)
    df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calcular_RSI(df, periodo=14):
    delta = df['close'].diff()
    ganancia = delta.where(delta > 0, 0)
    perdida = -delta.where(delta < 0, 0)
    media_ganancia = ganancia.rolling(periodo).mean()
    media_perdida = perdida.rolling(periodo).mean()
    rs = media_ganancia / media_perdida
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def detectar_niveles(df):
    df['rolling_min'] = df['low'].rolling(window=10).min()
    df['rolling_max'] = df['high'].rolling(window=10).max()
    soporte = round(df['rolling_min'].iloc[-2], 2)
    resistencia = round(df['rolling_max'].iloc[-2], 2)
    return soporte, resistencia

def graficar_alerta(df, par, soporte, resistencia):
    fig, ax1 = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    # --- Gráfico de precios ---
    ax1[0].plot(df['fecha'], df['close'], label='Precio', linewidth=1.8)
    ax1[0].axhline(soporte, color='green', linestyle='--', label='Soporte')
    ax1[0].axhline(resistencia, color='red', linestyle='--', label='Resistencia')
    ax1[0].set_title(f"{par} - Precio con Soporte y Resistencia")
    ax1[0].set_ylabel("Precio (USDT)")
    ax1[0].legend()
    ax1[0].grid(True, linestyle='--', alpha=0.4)

    # --- Gráfico RSI ---
    ax1[1].plot(df['fecha'], df['rsi'], label='RSI', color='purple')
    ax1[1].axhline(70, color='red', linestyle='--', linewidth=1)
    ax1[1].axhline(30, color='green', linestyle='--', linewidth=1)
    ax1[1].set_ylabel("RSI (14)")
    ax1[1].set_xlabel("Tiempo")
    ax1[1].grid(True, linestyle='--', alpha=0.4)
    ax1[1].legend()

    plt.tight_layout()

    imagen = BytesIO()
    plt.savefig(imagen, format='png', dpi=200)
    imagen.seek(0)
    plt.close(fig)
    return imagen

# ===== PROCESO PRINCIPAL =====
print("🤖 Bot avanzado con gráficos iniciado...\n")

# --- Enviar mensaje de prueba ---
bot.send_message(chat_id=CHAT_ID, text="✅ Bot iniciado y funcionando correctamente en Telegram.")

ultimo_envio = {}

while True:
    try:
        for par in CRIPTO_PARES:
            df = obtener_datos(par, INTERVALO)
            df = calcular_RSI(df)
            soporte, resistencia = detectar_niveles(df)
            precio = df['close'].iloc[-1]
            rsi = round(df['rsi'].iloc[-1], 2)

            mensaje = None

            if precio <= soporte and rsi < 35:
                mensaje = f"🟢 {par}\nTocó SOPORTE en ${precio}\nRSI={rsi} (posible rebote)"
            elif precio >= resistencia and rsi > 65:
                mensaje = f"🔴 {par}\nRompió RESISTENCIA en ${precio}\nRSI={rsi} (posible retroceso)"

            if mensaje and ultimo_envio.get(par) != mensaje:
                imagen = graficar_alerta(df, par, soporte, resistencia)
                bot.send_photo(chat_id=CHAT_ID, photo=imagen, caption=mensaje)
                ultimo_envio[par] = mensaje

            print(f"{par} | Precio: {precio} | RSI: {rsi} | Soporte: {soporte} | Resistencia: {resistencia}")

        print("⏰ Ciclo completado. Esperando siguiente revisión...\n")
        time.sleep(CICLO)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)

