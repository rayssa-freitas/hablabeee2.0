# Aplicacao de Busca de Locais com Google Maps API

Este projeto utiliza a API do Google Maps para buscar locais próximos com base em um endereço fornecido. Ele retorna informações detalhadas sobre os estabelecimentos encontrados e permite baixar os resultados em um arquivo CSV.

## Funcionalidades
- Busca locais de interesse próximos a uma coordenada (latitude, longitude).
- Exibe nome, endereço, status de funcionamento, horários, localização e viewport no mapa.
- Mostra os horários de funcionamento formatados e em português.
- Exporta resultados em CSV e TXT (incluindo horários de pico/fluxo de pessoas).
- Busca e exporta a movimentação de pessoas em cada local por dia/hora, usando scraping (google-popular-times).
- Interface web responsiva (Bootstrap).
- Possibilidade de rodar em modo CLI para automações e cargas em lote.

## Pré-requisitos

Antes de rodar a aplicação, instale os seguintes pacotes:

```sh
pip install -r requirements.txt
```

Também é necessário obter uma API Key do Google Maps e armazená-la no caminho `system/api_key.txt`.

## Como Usar

1. **Executar a aplicação**:
   ```sh
   python main.py web
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



