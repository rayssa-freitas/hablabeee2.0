import os  
import pandas as pd
import requests
from glob import glob
from setup import *
from places import search_places, get_api_key  # Importa funções atualizadas
from routes_matrix import *

# Verifica se a configuração inicial já foi feita
has_setup = open(r'system/has_setup.txt', 'r').read()
if has_setup == '0':
    os.system('python -m pip install --upgrade pip')
    os.system('pip install --upgrade python')
    os.system('pip install -r requirements.txt')
    has_setup = open(r'system/has_setup.txt', 'w').write('1')

clear_screen()
print(title)
build_wall(2)

globed = glob(f'{path_input}*.csv')
nbp = False
rm = False

api_key = get_api_key()  # Obtém a API Key antes de iniciar o processamento
if not api_key:
    print("Erro: API Key não encontrada! Verifique o arquivo de configuração.")
    exit()

for base in globed:
    name = base.split('\\')[-1]
    input_dataframe = pd.read_csv(base, sep=';', encoding='latin-1')
    opt = 0
    while opt != '':
        print((f'\n\n\n{separators}\nSelecione uma opção para continuar:\n\n'
               f'[1] Aplicar [blue]Search_places[/blue]\n'
               f'[2] Aplicar [green]RoutesMatrix[/green]\n'
               f'[3] [yellow]Concatenar[/yellow] e finalizar processo\n\n'
               f'[ENTER] [bright_red]Sair[/bright_red]\n\n{separators}\n'))
        opt = input('...')
        clear_screen()

        if opt == '1':
            for row in track(input_dataframe.index, description='Executando [green]NearbyPlaces...', 
                             style='black', complete_style='white', finished_style='green'):
                print(separators)
                empreendimento_nome = input_dataframe.at[row, 'txt_nome_do_empreendimento']
                latitude = str(input_dataframe.at[row, 'latitude'])
                longitude = str(input_dataframe.at[row, 'longitude'])
                coordinates = f"{latitude},{longitude}"
                
                print(f'\nAplicando Search_places para [purple]{empreendimento_nome}[/purple] nas coordenadas {coordinates}\n')
                
                search_places(api_key=api_key, coordinates=coordinates, input_dataframe=input_dataframe, row=row, 
                             empreendimento=empreendimento_nome, base=base)
            nbp = True

        elif opt == '2':
            routesMatrix()
            rm = True

        elif opt == '3':
            if not nbp and not rm:
                print((f'[bright_red]AVISO[/bright_red]\n{separators}\n'
                       f'Você parece não ter executado [green]DistanceMatrix[/green]({rm}) '
                       f'e [green]NearbyPlaces[/green]({nbp}).\nDeseja continuar mesmo assim?\n'
                       f'Concatenar DataFrames com colunas diferentes pode causar [red]erro[/red]...\n\n'
                       f'[0] Sim\n[ENTER] Não\n{separators}\n'))
                selection = input('...')
                clear_screen()
                if selection == '0':
                    concatenate_dataframes(output_name=name)
            else:
                concatenate_dataframes(output_name=name)

clear_screen()
print(title)
build_wall(5)
print('\nDeveloped by [bright_green]Rayssa[/bright_green]\n-\thttps://www.linkedin.com/in/rayssa-f-4b15941ba/\n-\t')