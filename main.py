import sys
import os
import json
import pandas as pd
import ast
import re

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, render_template_string
from glob import glob

from setup import *  # mantém seus helpers/constantes
from places import search_places, get_api_key, make_csv_filename
from routes_matrix import routesMatrix, concatenate_dataframes

app = Flask(__name__, static_folder="static", template_folder="templates")

# -------------------------------------------------------------------
# API Key
# -------------------------------------------------------------------
g_api_key = get_api_key()
if not g_api_key:
    print("Erro: API Key não encontrada! Verifique o arquivo system/api_key.txt")
    sys.exit(1)

# -------------------------------------------------------------------
# WEB
# -------------------------------------------------------------------
def run_web():
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/search', methods=['GET'])
    def do_search():
        place_type = request.args.get('type', '').strip()
        lat = request.args.get('lat', '').strip()
        lng = request.args.get('lng', '').strip()

        if not place_type or not lat or not lng:
            return jsonify({'error': 'Faltam parâmetros: type, lat, lng'}), 400

        print(f"Rodando search_places para {place_type} em ({lat}, {lng})")
        # Gera/atualiza o CSV
        search_places(lat, lng, place_type, api_key=g_api_key)

        csv_filename = make_csv_filename(place_type, lat, lng)
        csv_path = os.path.join("system", "results", csv_filename)
        download_url = f"/download/{csv_filename}"

        if not os.path.exists(csv_path):
            return jsonify({'error': 'Resultado não encontrado. Tente novamente.'}), 500

        results = []
        try:
            df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
            for _, row in df.iterrows():
                weekday_text_raw = row.get('weekday_text', '')
                try:
                    weekday_text_list = json.loads(weekday_text_raw)
                    if not isinstance(weekday_text_list, list):
                        weekday_text_list = ['Horário não informado']
                except Exception:
                    weekday_text_list = ['Horário não informado']

                weekday_map = {}
                for linha in weekday_text_list:
                    if ': ' in linha:
                        k, v = linha.split(': ', 1)
                        weekday_map[k] = v

                viewport = row.get('viewport', '{}')
                if isinstance(viewport, str):
                    try:
                        viewport = ast.literal_eval(viewport)
                    except Exception:
                        viewport = {}

                results.append({
                    'name': row.get('name', ''),
                    'city_state': row.get('city_state', ''),
                    'address': row.get('address', ''),
                    'business_status': row.get('business_status', ''),
                    'open_now': str(row.get('open_now', '')).strip().lower() == 'true',
                    'weekday_text': weekday_text_list,
                    'weekday_map': weekday_map,
                    'latitude': row.get('latitude', ''),
                    'longitude': row.get('longitude', ''),
                    'viewport': viewport
                })
        except Exception as e:
            print("Erro ao ler CSV:", e)
            return jsonify({'error': 'Erro ao ler resultados'}), 500

        return jsonify({
            'results': results,
            'download_url': download_url
        })

    @app.route('/download/<path:filename>')
    def download_file(filename):
        path = os.path.join("system", "results", filename)
        if not os.path.exists(path):
            abort(404, "Arquivo não encontrado.")
        return send_from_directory('system/results', filename, as_attachment=True)

    # (Opcional) ver tabela HTML de um arquivo específico
    @app.route('/view')
    def view():
        filename = request.args.get('file')
        if not filename:
            return "Informe ?file=<nome>.csv", 400
        csv_path = os.path.join('system', 'results', filename)
        if not os.path.exists(csv_path):
            return "Arquivo não encontrado", 404
        df = pd.read_csv(csv_path, sep=';')
        return render_template_string("""
            <h1>Resultados</h1>
            {{ table | safe }}
        """, table=df.to_html())

    app.run(debug=True)

# -------------------------------------------------------------------
# CLI (mantive sua lógica; lembre: precisa passar um place_type válido)
# -------------------------------------------------------------------
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
    api_key = g_api_key

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
                # ATENÇÃO: aqui é preciso decidir qual place_type usar.
                # Exemplo: rodar para TODOS os 'interest_zones':
                for zone_entry in interest_zones:
                    # cada item parece ser "label?raio?tipo"
                    try:
                        _, _, tipo = zone_entry.split('?')
                    except ValueError:
                        continue

                    for idx in df.index:
                        nome = df.at[idx, 'txt_nome_do_empreendimento']
                        lat = df.at[idx, 'latitude']
                        lng = df.at[idx, 'longitude']
                        coords = f"{lat},{lng}"
                        print(f"Buscando NearbyPlaces para {nome} em {coords} - tipo: {tipo}")
                        search_places(
                            api_key=api_key,
                            coordinates=coords,
                            place_type=tipo,
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

# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        run_web()
    else:
        run_cli()