import googlemaps
import requests
import os
import pandas as pd
import json

# -------------------------------------------------------------------
# API Key
# -------------------------------------------------------------------
def get_api_key(file_path='system/api_key.txt'):
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Erro: Arquivo {file_path} não encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler a API Key: {e}")
        return None

# -------------------------------------------------------------------
# Geocoding / Reverse
# -------------------------------------------------------------------
def get_coordinates(address, api_key):
    gmaps = googlemaps.Client(key=api_key)
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        print(f"Erro: Não foi possível encontrar coordenadas para o endereço: {address}")
        return None, None

def get_city_state(latitude, longitude, api_key):
    gmaps = googlemaps.Client(key=api_key)
    reverse_geocode_result = gmaps.reverse_geocode((latitude, longitude))
    if reverse_geocode_result:
        for result in reverse_geocode_result:
            address_components = result.get("address_components", [])
            city, state = None, None
            for component in address_components:
                if "administrative_area_level_2" in component["types"]:
                    city = component["long_name"]
                if "administrative_area_level_1" in component["types"]:
                    state = component["short_name"]
            if city and state:
                return f"{city}/{state}"
    return "Desconhecido"

# -------------------------------------------------------------------
# Helpers de horário e filename
# -------------------------------------------------------------------
def convert_to_24h(time_str):
    from datetime import datetime
    try:
        t = datetime.strptime(time_str, "%I:%M %p")
        return t.strftime("%H:%M")
    except Exception:
        return time_str

def format_weekday_text(weekday_text):
    dias_semana = {
        "Monday": "Segunda-feira",
        "Tuesday": "Terça-feira",
        "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira",
        "Friday": "Sexta-feira",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    if not isinstance(weekday_text, list) or not weekday_text:
        return ["Não disponível"]

    formatted_hours = []
    for entry in weekday_text:
        if ": " in entry:
            day_en, hours_raw = entry.split(": ", 1)
            day_pt = dias_semana.get(day_en, day_en)
            hours = hours_raw.strip()

            if hours.lower() == "open 24 hours":
                hours = "Aberto 24 horas"
            elif hours.lower() == "closed":
                hours = "Fechado"
            else:
                parts = hours.split(" / ")
                converted_parts = []
                for part in parts:
                    times = part.split("–")
                    if len(times) == 2:
                        start, end = times
                        start_24 = convert_to_24h(start.strip())
                        end_24 = convert_to_24h(end.strip())
                        converted_parts.append(f"{start_24} – {end_24}")
                    else:
                        converted_parts.append(part)
                hours = " / ".join(converted_parts)

            formatted_hours.append(f"{day_pt}: {hours}")
        else:
            formatted_hours.append(f"  - {entry}")
    return formatted_hours

def _fmt_coord(value):
    v = f"{float(str(value).replace(',', '.')):.5f}"
    return v.rstrip('0').rstrip('.') if '.' in v else v

def make_csv_filename(place_type, lat, lng):
    return f"{place_type}_near_{_fmt_coord(lat)}_{_fmt_coord(lng)}.csv"

# -------------------------------------------------------------------
# Places Details
# -------------------------------------------------------------------
def get_place_details(place_id, api_key):
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "opening_hours",
        "language": "pt-BR",
        "region": "BR"
    }
    response = requests.get(DETAILS_URL, params=params, timeout=5)
    data = response.json()
    if "result" in data and "opening_hours" in data["result"]:
        return data["result"]["opening_hours"].get("weekday_text", []), \
               data["result"]["opening_hours"].get("open_now", False)
    return [], False

# -------------------------------------------------------------------
# Nearby Search principal
# -------------------------------------------------------------------
def search_places(
    latitude: float | str = None,
    longitude: float | str = None,
    place_type: str | None = None,
    *,
    api_key: str | None = None,
    coordinates: str | None = None,
    input_dataframe=None,
    row=None,
    empreendimento: str | None = None,
    base: str | None = None
):
    key = api_key or get_api_key()
    if not key:
        print("Erro: API Key não encontrada!")
        return

    # Coordenadas
    if coordinates is not None:
        lat, lng = coordinates.split(",")
    else:
        lat, lng = latitude, longitude

    if not place_type:
        print("Erro: 'place_type' não informado.")
        return

    print(f"Buscando {place_type} perto de ({lat}, {lng})")

    city_state = get_city_state(lat, lng, key)

    PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": key,
        "location": f"{lat},{lng}",
        "type": place_type,          # <— aqui
        "rankby": "distance",
        "language": "pt-BR",         # <— ajuda na consistência de idioma
        "region": "BR"
    }

    response = requests.get(PLACES_URL, params=params, timeout=10)
    data = response.json()

    places_list = []
    if "results" in data:
        for place in data["results"]:
            place_id = place.get("place_id")
            if place_id:
                weekday_text, open_now = get_place_details(place_id, key)
                if not isinstance(weekday_text, list) or not weekday_text:
                    formatted_weekday = ["Não disponível"]
                else:
                    formatted_weekday = format_weekday_text(weekday_text)
                print("Horários brutos retornados:", weekday_text)
            else:
                weekday_text = []
                open_now = None
                formatted_weekday = []
                print("Horários brutos retornados: Não disponível (place_id ausente)")
            
            tipos = place.get("types", [])
            viewport = place.get("geometry", {}).get("viewport", {})
            places_list.append({
                "id": place_id,
                "city_state": city_state,
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "open_now": bool(open_now),
                "business_status": place.get("business_status"),
                "latitude": place["geometry"]["location"]["lat"],
                "longitude": place["geometry"]["location"]["lng"],
                "weekday_text": json.dumps(formatted_weekday, ensure_ascii=False),
                "types": json.dumps(tipos, ensure_ascii=False),
                "search_type": str(place_type), 
                "viewport": viewport
            })

    if not places_list:
        print(f"Nenhum resultado encontrado para {place_type} no local especificado.")
        return

    # Salvar CSV no padrão unificado
    csv_filename = make_csv_filename(place_type, lat, lng)
    file_path = os.path.join("system", "results", csv_filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        pd.DataFrame(places_list).to_csv(file_path, sep=';', index=False, encoding='utf-8-sig')
        print(f"Resultados salvos em: {file_path}")
        return file_path
    except Exception as e:
        print(f"Erro ao salvar o CSV: {e}")
        return
