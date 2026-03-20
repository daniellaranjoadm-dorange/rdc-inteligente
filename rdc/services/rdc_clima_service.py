from urllib.parse import urlencode
from urllib.request import urlopen
import json

from .rdc_excel_layout_service import (
    LATITUDE_OBRA,
    LONGITUDE_OBRA,
    TIMEZONE_OBRA,
    FILL_SOL,
    FILL_NUBLADO,
    FILL_CHUVA,
)


def _traduzir_weather_code(weather_code):
    mapa = {
        0: "Céu limpo",
        1: "Predominantemente limpo",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Nevoeiro",
        48: "Nevoeiro com geada",
        51: "Garoa leve",
        53: "Garoa moderada",
        55: "Garoa intensa",
        61: "Chuva leve",
        63: "Chuva moderada",
        65: "Chuva forte",
        80: "Pancadas de chuva leves",
        81: "Pancadas de chuva moderadas",
        82: "Pancadas de chuva fortes",
        95: "Trovoada",
        96: "Trovoada com granizo leve",
        99: "Trovoada com granizo forte",
    }
    return mapa.get(weather_code, f"Código climático {weather_code}")


def _classificar_clima_visual(descricao):
    txt = str(descricao or "").upper()
    if any(p in txt for p in ["CHUVA", "TROVOADA", "GAROA", "PANCADAS"]):
        return {"coluna": "CHUVA", "emoji": "🌧", "fill": FILL_CHUVA}
    if any(p in txt for p in ["NUBLADO", "NEVOEIRO", "PARCIALMENTE"]):
        return {"coluna": "NUBLADO", "emoji": "☁", "fill": FILL_NUBLADO}
    return {"coluna": "SOL", "emoji": "☀", "fill": FILL_SOL}


def buscar_clima_online_rio_grande(data):
    try:
        params = urlencode(
            {
                "latitude": LATITUDE_OBRA,
                "longitude": LONGITUDE_OBRA,
                "timezone": TIMEZONE_OBRA,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "start_date": data.strftime("%Y-%m-%d"),
                "end_date": data.strftime("%Y-%m-%d"),
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        with urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        daily = payload.get("daily", {})
        current = payload.get("current", {})
        weather_code = daily.get("weather_code", [None])[0]
        if weather_code is None:
            weather_code = current.get("weather_code")

        descricao = _traduzir_weather_code(weather_code) if weather_code is not None else "Clima não identificado"
        return {
            "descricao": descricao,
            "temperatura_atual": current.get("temperature_2m"),
            "temperatura_max": daily.get("temperature_2m_max", [None])[0],
            "temperatura_min": daily.get("temperature_2m_min", [None])[0],
            "chuva_mm": daily.get("precipitation_sum", [None])[0],
            "vento_kmh": current.get("wind_speed_10m"),
            "visual": _classificar_clima_visual(descricao),
        }
    except Exception:
        descricao = "Clima não disponível"
        return {
            "descricao": descricao,
            "temperatura_atual": None,
            "temperatura_max": None,
            "temperatura_min": None,
            "chuva_mm": None,
            "vento_kmh": None,
            "visual": _classificar_clima_visual(descricao),
        }
