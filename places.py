import googlemaps
import requests
import os
import pandas as pd
import json
from flask import Flask, send_file, abort
import populartimes
import requests
from setup import interest_zones, path_system

# Função para obter a API Key do arquivo
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

# Função para converter um endereço em coordenadas geográficas
def get_coordinates(address, api_key):
    gmaps = googlemaps.Client(key=api_key)
    geocode_result = gmaps.geocode(address)
    
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        print(f"Erro: Não foi possível encontrar coordenadas para o endereço: {address}")
        return None, None

# Função para obter detalhes do local, incluindo horários completos
def get_place_details(place_id, api_key):
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "opening_hours"
    }
    
    response = requests.get(DETAILS_URL, params=params, timeout=5)
    data = response.json()
    
    if "result" in data and "opening_hours" in data["result"]:
        return data["result"]["opening_hours"].get("weekday_text", []), \
            data["result"]["opening_hours"].get("open_now", False)
    return [], False

# Função para formatar os horários de funcionamento de forma organizada
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

    formatted_hours = []

    if not isinstance(weekday_text, list) or not weekday_text:
        return ["Não disponível"]
    
    
    for entry in weekday_text:
        # Exemplo de entrada: "Monday: 7:00 AM – 8:00 PM"
        if ": " in entry:
            day_en, hours_raw = entry.split(": ", 1)
            day_pt = dias_semana.get(day_en, day_en)

            # Ajustar horários para 24h e texto personalizado:
            hours = hours_raw.strip()

            # Tratamento de "Open 24 hours"
            if hours.lower() == "open 24 hours":
                hours = "Aberto 24 horas"
            elif hours.lower() == "closed":
                hours = "Fechado"
            else:
                # Converter horário de AM/PM para 24h (se possível)
                # Exemplo: "7:00 AM – 8:00 PM" para "07:00 – 20:00"
                parts = hours.split(" / ")  # múltiplos intervalos no dia
                converted_parts = []
                for part in parts:
                    # part = "7:00 AM – 8:00 PM"
                    times = part.split("–")
                    if len(times) == 2:
                        start, end = times
                        start_24 = convert_to_24h(start.strip())
                        end_24 = convert_to_24h(end.strip())
                        converted_parts.append(f"{start_24} – {end_24}")
                    else:
                        converted_parts.append(part)
                hours = " / ".join(converted_parts)

            formatted_hours.append(f"{day_en}: {hours}")

        else:
            formatted_hours.append(f"  - {entry}")

    return formatted_hours

def convert_to_24h(time_str):
    # time_str exemplo: "7:00 AM"
    from datetime import datetime
    try:
        t = datetime.strptime(time_str, "%I:%M %p")
        return t.strftime("%H:%M")
    except Exception:
        # fallback
        return time_str

def get_popular_times(api_key, place_id):
    try:
        # Busca por popular times de um único local pelo place_id
        res = populartimes.get_id(api_key, place_id)
        if 'populartimes' in res:
            return res['populartimes']
        else:
            return None
    except Exception as e:
        print(f'Erro ao obter popular times: {e}')
        return None
    
def normalize_popular_times(populartimes_data):
    # populartimes_data: [{'name': 'Monday', 'data': [0, 5, 10, ...]}]
    records = []
    for day_info in populartimes_data:
        day = day_info["name"]
        values = day_info["data"]
        max_val = max(values) if values and max(values) > 0 else 1
        normalized = [round(v / max_val, 2) for v in values]
        for hour, score in enumerate(normalized):
            records.append({
                "day": day_info["name"],
                "hour": hour,
                "movement": score
            })
    return pd.DataFrame(records)

    return pd.DataFrame(records)

def save_peak_hours_txt(df: pd.DataFrame, filename: str):
    """
    Salva o DataFrame de horários de pico em TXT tab-delimitado.
    Garante que o diretório exista.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename, sep='\t', index=False, encoding='utf-8-sig')
    print(f"Arquivo de pico salvo em: {filename}")
            
# Função para obter a cidade/estado correspondents as coordenadas
def get_city_state(latitude, longitude, api_key):
    gmaps = googlemaps.Client(key=api_key)
    reverse_geocode_result = gmaps.reverse_geocode((latitude, longitude))

    if reverse_geocode_result:
        for result in reverse_geocode_result:
            address_components = result.get("address_components", [])
            city, state = None, None
            for component in address_components:
                if "administrative_area_level_2" in component["types"]:  # Cidade
                    city = component["long_name"]
                if "administrative_area_level_1" in component["types"]:  # Estado
                    state = component["short_name"]
            if city and state:
                return f"{city}/{state}"
    
    return "Desconhecido"

# Função para buscar estabelecimentos próximos usando a API Places
def search_places(
    latitude: float | str = None,
    longitude: float | str = None,
    place_type: str = None,
    *,
    api_key: str | None = None,
    coordinates: str | None = None,
    input_dataframe=None,
    row=None,
    empreendimento: str | None = None,
    base: str | None = None
):
    key = api_key or get_api_key() 
    if not api_key:
        print("Erro: API Key não encontrada!")
        return

    if coordinates is not None:
        lat, lng = coordinates.split(",")
        place_type = empreendimento
    else:
        lat, lng = latitude, longitude

    print(f"Buscando {place_type} perto de ({lat}, {lng})")
    
    city_state = get_city_state(lat, lng, api_key)

    # Configuração da API Places
    PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": key,
        "location": f"{lat},{lng}",
        "keyword": place_type,
        "rankby": "distance",
        "fields": "geometry.viewport"
    }
    
    # Fazendo a requisição
    response = requests.get(PLACES_URL, params=params, timeout=5)
    data = response.json()
        
    # Processando os resultados
    places_list = []
    if "results" in data:
        for place in data["results"]:
            place_id = place.get("place_id")
            if place_id:
                weekday_text, open_now = get_place_details(place_id, api_key)
                if not isinstance(weekday_text, list):
                    weekday_text = []
                formatted_weekday = format_weekday_text(weekday_text)
                print("Horários brutos retornados:", weekday_text)
            else:
                weekday_text = []
                open_now = None
                formatted_weekday = []
                print("Horários brutos retornados: Não disponível (place_id ausente)")
            
            viewport = place.get("geometry", {}).get("viewport", {})

            places_list.append({
                "id": place_id,
                "city_state": city_state,
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "open_now": open_now if open_now is not None else False,
                "business_status": place.get("business_status"),
                "latitude": place["geometry"]["location"]["lat"],
                "longitude": place["geometry"]["location"]["lng"],
                "weekday_text": json.dumps(formatted_weekday, ensure_ascii=False),
                "viewport": viewport
            })
        print("Horários brutos retornados:", weekday_text)

    if not places_list:
        print(f"Nenhum resultado encontrado para {place_type} no local especificado.")
        return

    # Criando DataFrame e salvando os resultados
    df = pd.DataFrame(places_list)
    file_name = f"system/results/{place_type}_near_{lat}_{lng}.csv"
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    
    
    try:
        df.to_csv(file_name, sep=';', index=False, encoding='utf-8-sig')
        print(f"Resultados salvos em: {file_name}")
        
        peak_tables = []
        for place in places_list:
            pop_data = get_popular_times(key, place['id'])
            if pop_data:
                df_norm = normalize_popular_times(pop_data)
                # adiciona colunas de identificação do local
                df_norm.insert(0, 'place_id',   place['id'])
                df_norm.insert(1, 'place_name', place['name'])
                peak_tables.append(df_norm)

            if peak_tables:
                df_peak = pd.concat(peak_tables, ignore_index=True)
            else:
                # gera um DataFrame vazio com as colunas
                df_peak = pd.DataFrame(columns=["place_id","place_name","day","hour","movement"])

            txt_name = f"{place_type}_near_{lat}_{lng}_popular_times.txt"
            txt_path = os.path.join(path_system, "results", txt_name)
            save_peak_hours_txt(df_peak, txt_path)
            print(f"Horários de pico salvos em: {txt_path}")
    
        return file_name

    except Exception as e:
        print(f"Erro ao salvar o CSV: {e}")
    
    # Exibir os resultados no terminal
    for place in places_list:
        print(f"\nNome: {place['name']}")
        print(f"Cidade/Estado: {place['city_state']}")
        print(f"Endereço: {place['address']}")
        print(f"Status: {place['business_status']}")
        print(f"Está aberto agora? {'Sim' if place['open_now'] else 'Não'}")
        print("Horários da Semana:\n" + "\n".join(format_weekday_text(place['weekday_text'])))
        print(f"Localização: {place['latitude']}, {place['longitude']}")
        print(f"Viewport: {place['viewport']}")

app = Flask(__name__)

# Função para fazer o download da planilha CSV automaticamente
@app.route("/download")
def download_file():
    directory = "system/results"
    file_name = "output_places.csv" 
    file_path = os.path.join(directory, file_name)

    if not os.path.exists(file_path):
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return abort(404, description="Arquivo não encontrado.")

    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
    
# Teste da função com um endereço fixo
    api_key = get_api_key()
    search_places(-27.5828, -48.5047, "health_center")