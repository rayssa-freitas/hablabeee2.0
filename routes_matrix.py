# Aqui é executada a função distance matrix da biblioteca googlemaps
# usando como origem as coordenadas do local buscado, e como destinos
# todos os retornos da função nearbyPlaces registrados no dataframe.
# O json retornado é percorrido e as informações desejadas são registradas
# junto ao dataframe.

from setup import *

def routesMatrix():
    globed = glob(f'{path_system}*&.csv')
    for caso in track(globed, description='Aplicando [green]DistanceMatrix...', style='black', complete_style='white', finished_style='green'):
        print(separators)
        df = pd.read_csv(caso, sep=';')
        coord = caso.split('&')[2]
        coord = coord.split('+')
        pin_point = {'lat': coord[0].replace(',', '.'), 'lng': coord[1].replace(',', '.')}
        coord_destinations = []
        for i in df.index:
            json_format = df.at[i, 'coordenada_do_local'].replace("'", "\"")
            json_format = json.loads(json_format)
            coord_destinations.append(json_format)
        print(f'Searching [green]Matrix[/green] for [deep_pink4]{caso}[/deep_pink4] with coordinates {pin_point}\n')
        response = client.distance_matrix(
            origins=pin_point,
            destinations=coord_destinations,
            mode='walking',
            language='pt-BR',
            units='metric'
        )

        try:        
            rows = response.get('rows')[0].get('elements')
            print(f'[purple]Returned[/purple]:\n{response}\n')
            df_response = pd.DataFrame(rows)
            df_response.drop(columns=['status'], axis=1, inplace=True)

            for i in df_response.index:
                minutos = int(df_response.at[i, 'duration'].get('value')) / 60
                df_response.at[i, 'distance'] = df_response.at[i, 'distance'].get('value')
                df_response.at[i, 'duration'] = round(minutos, 2)
            df_response.columns = ['distancia(metros)', 'tempo_de_viagem(minutos)']
            print(f'DataFrame from response:\n{df_response}\n\n')

            df_response = pd.concat([df, df_response], axis=1)
            print(f'DataFrame concatenated:\n{df_response}\n\n')
            print(f'\n[green]Updating[/green] CSV [purple]{caso}[/purple]\n')
            df_response = drop_unnamed(df_response)
            updt_name = f"{caso.split('.csv')[0]}MATRIX_APPLIED.csv"
            df_response.to_csv(updt_name, sep=';')
            os.remove(caso)
            print(f'[yellow]Created {updt_name}\n\n')
        except:
            empreendimento = caso.split('&')[1]
            row = 0
            print('\n[bright_red]WARNING:[/bright_red] Response not expected\nCSV will not be updated, [yellow]txt file with description will be created instead[/yellow]\n')
            error_description = f"Problem: Could not create a proper DataFrame for API response\n\nName: {empreendimento}\n\nCoordinates: {pin_point}\n\nOrigin DataFrame: {caso}\n\nAPI Response: {response}" # CEP: {df.at[row, 'txt_cep']} / Vicinity: {df.at[row, 'txt_uf']} {df.at[row, 'txt_municipio']} {df.at[row, 'txt_endereco']}
            with open(f'system/problems/MATRIX_at_{empreendimento}.txt', 'w', encoding="latin-1") as file:
                file.write(error_description)
