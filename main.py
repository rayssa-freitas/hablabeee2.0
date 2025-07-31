import sys
import os
import pandas as pd
import ast
import re

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, render_template_string, jsonify
from glob import glob
from setup import *
from places import search_places, get_api_key
from routes_matrix import routesMatrix, concatenate_dataframes

app = Flask(__name__, static_folder="static", template_folder="templates")

g_api_key = get_api_key()
if not g_api_key:
    print("Erro: API Key não encontrada! Verifique o arquivo system/api_key.txt")
    sys.exit(1)

def convert_12h_to_24h(match):
    h = int(match.group(1))
    m = match.group(2)
    ampm = match.group(3).upper()
    if ampm == 'PM' and h != 12:
        h += 12
    if ampm == 'AM' and h == 12:
        h = 0
    return f"{h:02d}:{m}"

def format_weekday_text(weekday_text_list):
    dias_pt = [
        'Segunda-feira', 'Terça-feira', 'Quarta-feira',
        'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ]
    mapa_en_pt = {
        'Monday': 'Segunda-feira',
        'Tuesday': 'Terça-feira',
        'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira',
        'Friday': 'Sexta-feira',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    horarios = {}

    for linha in (weekday_text_list or []):
        linha = linha.replace('\u202f', ' ').replace('\u2009', ' ').strip()
        partes = linha.split(': ', 1)
        if len(partes) != 2:
            continue
        dia_en, horas = partes
        dia_pt = mapa_en_pt.get(dia_en.strip(), dia_en.strip())

        if not horas or 'closed' in horas.lower():
            horarios[dia_pt] = 'Fechado'
        elif 'open 24 hours' in horas.lower():
            horarios[dia_pt] = 'Aberto 24 horas'
        else:
            intervalos = []
            for intervalo in horas.split(','):
                intervalo = intervalo.strip()
                intervalo = re.sub(r'(\d{1,2}):(\d{2}) ?(AM|PM)', convert_12h_to_24h, intervalo, flags=re.IGNORECASE)
                intervalo = re.sub(r'\s?[–-]\s?', ' – ', intervalo)
                intervalos.append(intervalo)
            horarios[dia_pt] = ' / '.join(intervalos)

    resultado = ''
    for dia in dias_pt:
        resultado += f"{dia}: {horarios.get(dia, 'Fechado')}\n"
    return resultado

# --- MODO WEB ---
def run_web():
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/search', methods=['GET'])
    def do_search():
        zone = request.args.get('type')
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))

        if not zone or not lat or not lng:
            return jsonify({'error': 'Faltam parâmetros'}), 400

        print(f"Rodando search_places para {zone} em ({lat}, {lng})")
        search_places(lat, lng, zone, api_key=g_api_key)

        csv_filename = f"{zone}_near_{lat}_{lng}.csv"
        csv_path = os.path.join("system/results", csv_filename)
        download_url = f"/download/{csv_filename}"

        results = []

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                df = pd.read_csv(f, sep=';')
            for _, row in df.iterrows():
                weekday_text_raw = row.get('weekday_text', '')
                if isinstance(weekday_text_raw, str):
                    weekday_text_list = json.loads(weekday_text_raw)
                    if weekday_text_list == ["Não disponível"]:
                        weekday_text_list = ['Horário não informado']
                else:
                    weekday_text_list = ['Horário não informado']

                results.append({
                    'name': row.get('name', ''),
                    'city_state': row.get('city_state', ''),
                    'address': row.get('address', ''),
                    'business_status': row.get('business_status', ''),
                    'open_now': str(row.get('current_opening_hours', '')).strip().lower() == 'true',
                    'weekday_text': weekday_text_list,
                    'latitude': row.get('latitude', ''),
                    'longitude': row.get('longitude', ''),
                    'viewport': ast.literal_eval(row.get('viewport', '{}')) if isinstance(row.get('viewport'), str) else {}
                })
        except Exception as e:
            print("Erro ao ler CSV:", e)
            return jsonify({'error': 'Erro ao ler resultados'}), 500

        #teste   
        print("weekday_text_raw:", weekday_text_raw)
        print("weekday_text_list:", weekday_text_list)

        return jsonify({
            'results': results,
            'download_url': download_url
        })

    @app.route('/download/<path:filename>')
    def download_file(filename):
        path = os.path.join("system/results", filename)
        if not os.path.exists(path):
            abort(404, "Arquivo não encontrado.")
        return send_from_directory('system/results', filename, as_attachment=True)

    app.run(debug=True)

    @app.route('/view')
    def view():
        filename = 'theater_near_-0.0101_-51.0512.csv'
        df = pd.read_csv(os.path.join('system', 'results', filename))
        return render_template_string("""
            <h1>Resultados</h1>
            {{ table | safe }}
        """, table=df.to_html())

    app.run(debug=True)

# --- MODO CLI ---
def run_cli():
    has_setup = open(os.path.join(path_system, 'has_setup.txt'), 'r').read().strip()
    if has_setup == '0':
        os.system('pip install --upgrade pip')
        os.system('pip install -r requirements.txt')
        open(os.path.join(path_system, 'has_setup.txt'), 'w').write('1')

    clear_screen()
    print(title)
    build_wall(2)

    files = glob(f'{path_input}*.csv')
    nbp = rm = False
    api_key = get_api_key()
    if not api_key:
        print("Erro: API Key não encontrada!")
        sys.exit(1)

    for base in files:
        name = os.path.basename(base)
        df = pd.read_csv(base, sep=';', encoding='latin-1')
        opt = None

        while opt != '':
            print(f"""\n{separators}
[1] NearbyPlaces   [2] RoutesMatrix   [3] Concatenar & Sair   [ENTER] Sair
{separators}""")
            opt = input('> ').strip()
            clear_screen()

            if opt == '1':
                for idx in df.index:
                    nome = df.at[idx, 'txt_nome_do_empreendimento']
                    lat = df.at[idx, 'latitude']
                    lng = df.at[idx, 'longitude']
                    coords = f"{lat},{lng}"
                    print(f"Buscando NearbyPlaces para {nome} em {coords}")
                    search_places(
                        api_key=api_key,
                        coordinates=coords,
                        input_dataframe=df,
                        row=idx,
                        empreendimento=nome,
                        base=base
                    )
                nbp = True

            elif opt == '2':
                routesMatrix()
                rm = True

            elif opt == '3':
                if not nbp and not rm:
                    print("Ainda não fez NearbyPlaces nem RoutesMatrix. Forçar concatenação? (0=sim)")
                    if input('> ').strip() == '0':
                        concatenate_dataframes(output_name=name)
                else:
                    concatenate_dataframes(output_name=name)

    clear_screen()
    print(title)
    build_wall(2)
    print("\nDeveloped by Rayssa — https://www.linkedin.com/in/rayssa-f-4b15941ba/\n")

# --- PONTO DE ENTRADA ---
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        run_web()
    else:
        run_cli()
