# Aplicacao de Busca de Locais com Google Maps API

Este projeto utiliza a API do Google Maps para buscar locais próximos com base em um endereço fornecido. Ele retorna informações detalhadas sobre os estabelecimentos encontrados e permite baixar os resultados em um arquivo CSV.

## Funcionalidades
- Buscar locais próximos a um endereço utilizando a API Places do Google.
- Obter coordenadas geográficas de um endereço.
- Consultar horários de funcionamento de estabelecimentos.
- Exportar os resultados em um arquivo CSV.
- Servir o arquivo CSV para download via Flask.

## Pré-requisitos

Antes de rodar a aplicação, instale os seguintes pacotes:

```sh
pip install googlemaps requests pandas flask
```

Também é necessário obter uma API Key do Google Maps e armazená-la no caminho `system/api_key.txt`.

## Como Usar

1. **Executar a aplicação**:
   ```sh
   python main.py
   ```

2. **Buscar locais próximos**:
   - A busca é feita chamando a função `search_places` dentro de places.py.
   - Exemplo de uso:
     ```python
     search_places(latitute, longitude, "museum")
     ```

3. **Fazer download do CSV**:
   - Após rodar a busca, acesse no navegador:
     ```
     http://127.0.0.1:5000/download
     ```
   - O arquivo CSV será baixado automaticamente.

## Estrutura do Projeto
```
project-folder/
│-- main.py
│-- places.py
│-- routes_matrix.py
│-- setup.py
│-- system/
│   ├── api_key.txt
│   ├── results/
│-- README.md
```



