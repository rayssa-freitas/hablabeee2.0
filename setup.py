# Aqui dentro são criadas as variáveis a serem usadas pelo sistema, além de serem feitos os imports
# e a instalação/atualização de pacotes


# Importação de bibliotecas
import pandas as pd
import googlemaps
import json
from glob import glob
from rich.progress import track
from rich.traceback import install
from rich import print
from datetime import datetime
import warnings
import os

# Impede avisos desnecessários aos usuários
warnings.filterwarnings('ignore')
install()


# Define os caminhos dos diretórios pelo sistema
path_system = r'system/'
path_input = r'input/'
path_output = r'output/'
path_key = f'{path_system}api_key.txt'


# Lê a chave de acesso ao Google Maps API
key = open(path_key, 'r').read()
client = googlemaps.Client(key)


# Lista de zonas de interesse a ser buscado via API
interest_zones = [
    "escola publica?5?school", 
    "hospital?5?hospital",
    "cinema?5?movie_theater",
    "teatro?5?theater", 
    "aeroporto?5?airport",
    "rodoviaria?5?bus_station",
    "centro de convenções?5?convention_center", 
    "museu?5?museum",
    "hotel?5?hotel",
    "pousada?5?guesthouse",
    "shopping center?5?shopping_center",
    "centro comercial?5?business",
    "varejo?5?retail",
    "loja?5?shop",
    "restaurante?5?restaurant",
    "universidade?5?university",
    "posto de saude?5?health_center",
    ]


# Função para concatenar vários arquivos de resultados em um só
def concatenate_dataframes(output_name: str):
    concat_glob = glob(f'{path_system}*MATRIX_APPLIED.csv')
    concat_df = pd.read_csv(concat_glob.pop(0), sep=';')
    for cache in track(concat_glob, description=f'Concatenando DataFrames...', style='black', complete_style='white', finished_style='green'):
        new_df = pd.read_csv(cache, sep=';')
        concat_df = pd.concat([concat_df, new_df], axis=0, ignore_index=True)
    concat_df = drop_unnamed(concat_df)
    now = datetime.now().strftime('%d-%m-%Y_%H-%M')
    concat_df.to_csv(f'{path_output}hab_entorno_{now}_{output_name}', sep=';')
    print(f'\n[yellow]CSV {path_output}hab_entorno_{now}_{output_name} successfully created')

# Função auxiliar para remover colunas "Unnamed" geradas pelo pandas
def drop_unnamed(df: pd.DataFrame):
    unnamed_list = []
    for unnamed in df.columns:
        if 'Unnamed' in unnamed:
            unnamed_list.append(unnamed)
    df.drop(unnamed_list, axis=1, inplace=True)
    return df

# Identifica duplicidade de locais com coordenadas idênticas ou semelhantes
def match_coordinates(lat, lng, vicinity, place_name, cache_coordinates:dict, cache_vicinity:str, cache_name:str):
    if str(lat)[:7] == str(cache_coordinates['lat'])[:7] and str(lng)[:7] == str(cache_coordinates['lng'])[:7]:
        print(f'[bright_red]Found same coordinates for different places, adding it to a remove list for future removal[/bright_red]\nPlace:{place_name} {vicinity} ({lat} {lng})\nPlace at cache: {cache_name} {cache_vicinity} ({cache_coordinates})')
        message = f'Found places with same coordinates\n\n{"- "*20}\nSaved at cache: {cache_name}\nVicinity: {cache_vicinity}\nCoordinates: {cache_coordinates}\n{"- "*20}\n\nPlace next to it: {place_name}\nVicinity: {vicinity}\nCoordinates: {lat} {lng}\n'
        open(f'system/problems/SAME_COORDINATES_AT_{str(lat)[:10]}+{str(lng)[:10]}_AND_{str(cache_coordinates["lat"])[:10]}+{str(cache_coordinates["lng"])[:10]}.txt', 'w', encoding="utf-8").write(message)
        return True
    elif str(lat)[:5] == str(cache_coordinates['lat'])[:5] and str(lng)[:5] == str(cache_coordinates['lng'])[:5]:
        if vicinity[:15] == cache_vicinity[:15]:
            print(f'[bright_red]Found lookalike coordinates and vicinities for different places, adding it to a remove list for future removal[/bright_red]\nPlace: {vicinity} ({lat} {lng})\nPlace at cache: {cache_name} {cache_vicinity} ({cache_coordinates})')
            message = f'Found places with same lookalike coordinates and vicinities\n\n{"- "*20}\nSaved at cache: {cache_name}\nVicinity: {cache_vicinity}\nCoordinates: {cache_coordinates}\n{"- "*20}\n\nPlace next to it: {place_name}\nVicinity: {vicinity}\nCoordinates: {lat} {lng}\n'
            open(f'system/problems/LOOKALIKE_PLACES_AT_{str(lat)[:10]}+{str(lng)[:10]}_AND_{str(cache_coordinates["lat"])[:10]}+{str(cache_coordinates["lng"])[:10]}.txt', 'w', encoding="utf-8").write(message)
            return True
        else:
            return False
    else:
        return False

# ASCII ART/CONFIGS 

title = """\n█▀▀ █▄░█ ▀█▀ █▀█ █▀█ █▄░█ █▀█   ▄▄   █░█ ▄▀█ █▄▄ █░░ ▄▀█ █▄▄ █▀▀ █▀▀ █▀▀
██▄ █░▀█ ░█░ █▄█ █▀▄ █░▀█ █▄█   ░░   █▀█ █▀█ █▄█ █▄▄ █▀█ █▄█ ██▄ ██▄ ██▄"""

wall = """_|___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|
___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|___|__\n"""

wall_top = '______________________________________________________________________'

def build_wall(n: int = 1):
    # imprime a “parede” n vezes
    print('\n'.join([wall_top] * n))
    
# Limpa a tela do terminal 
clean = '\n'*50
def clear_screen():
    print(clean)

# Separador visual usado nos menus
separators = '>'*50
