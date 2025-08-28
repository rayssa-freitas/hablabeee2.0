# batch_runner_pairs.py
import os
import re
import time
import argparse
import pandas as pd
from glob import glob

# usa o que você já tem no projeto
from setup import interest_zones  # lista "label?raio?tipo"
from places import search_places, get_api_key  # sua função que gera os CSVs
from regions import infer_region_from_csv, move_to_region_folder

try:
    from places import make_csv_filename  # normalizador de nome com 5 casas
except Exception:
    def make_csv_filename(place_type, lat, lng):
        return f"{place_type}_near_{lat}_{lng}.csv"

RESULTS_DIR = os.path.join("system", "results")

# --------- tipologias a partir do setup.interest_zones ----------
def parse_interest_types(zones):
    """
    Retorna:
      - types: lista única preservando ordem (3º campo de cada item)
      - label2type: mapeia o 'label' (1º campo) -> 'type'
    """
    types, seen = [], set()
    label2type = {}
    for z in zones:
        parts = str(z).split("?")
        if len(parts) >= 3:
            label = parts[0].strip().lower()
            t = parts[2].strip()
            label2type[label] = t
            if t not in seen:
                types.append(t)
                seen.add(t)
    return types, label2type

# permite o usuário passar nomes amigáveis ou os types já prontos
def resolve_types(user_csv: str | None, zones):
    all_types, label2type = parse_interest_types(zones)
    if not user_csv:
        return all_types
    out, seen = [], set()
    for raw in user_csv.split(","):
        k = raw.strip().lower()
        t = label2type.get(k, k)  # se for label, converte; se já for type, mantém
        if t not in seen:
            out.append(t); seen.add(t)
    return out

# --------- helpers para extrair coordenadas de células "Lat, Long" ----------
def _parse_latlng_cell(val):
    """
    Aceita string com um par 'lat, lng' (com/sem parênteses, vírgula ou ponto como decimal).
    Ex.: '-23.5505, -46.6333' ou '-23,5505, -46,6333' ou '( -23.55 , -46.63 )'
    Retorna (lat, lng) como float, ou None.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    nums = re.findall(r'[-+]?\d+(?:[.,]\d+)?', s)
    if len(nums) < 2:
        return None

    def to_float_pt(x):
        x = x.strip()
        # se tem vírgula e não tem ponto, trate vírgula como decimal
        if ',' in x and '.' not in x:
            x = x.replace(',', '.')
        return float(x)

    try:
        lat = to_float_pt(nums[0])
        lng = to_float_pt(nums[1])
        return (lat, lng)
    except Exception:
        return None

def read_coords_table(path: str, pair_cols_filter: list[str] | None = None) -> pd.DataFrame:
    """
    Lê CSV/Excel e retorna um DF padronizado com:
      latitude | longitude | name | source_col
    Regras:
      1) Se houver colunas separadas (lat/lng), usa direto.
      2) Caso contrário, varre colunas que aparentam conter pares '(Lat, Long)'
         (ex.: 'Centro da Cidade (Lat, Long)') e extrai TODAS as células preenchidas.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        # precisa de openpyxl instalado
        df = pd.read_excel(path)
    else:
        # tenta ; e cai para , se necessário
        try:
            df = pd.read_csv(path, sep=";", engine="python")
        except Exception:
            df = pd.read_csv(path, sep=",", engine="python")

    # 1) tentar lat/lng separados
    lower = {c.lower().strip(): c for c in df.columns}
    lat_col = next((lower[k] for k in lower if k in ("lat", "latitude")), None)
    lng_col = next((lower[k] for k in lower if k in ("lng", "long", "lon", "longitude")), None)
    name_col = next((lower[k] for k in lower if "nome" in k or "empreendimento" in k or "name" in k), None)

    if lat_col and lng_col:
        cols = [lat_col, lng_col] + ([name_col] if name_col else [])
        out = df[cols].copy()
        out.columns = ["latitude", "longitude"] + (["name"] if name_col else [])
        out["source_col"] = lat_col + " & " + lng_col
        return out

    # 2) identificar colunas "par" (Lat, Long)
    def looks_like_pair(colname: str) -> bool:
        cl = colname.lower()
        return ("lat" in cl and "long" in cl) or ("lat, long" in cl) or ("(lat" in cl and "long" in cl)

    pair_cols = [c for c in df.columns if looks_like_pair(c)]
    if pair_cols_filter:
        pair_cols = [c for c in pair_cols if c in pair_cols_filter]

    # fallback: detectar por conteúdo (duas ocorrências numéricas nas células)
    if not pair_cols:
        for c in df.columns:
            sample = df[c].dropna().astype(str).head(5).tolist()
            if any(len(re.findall(r'[-+]?\d+(?:[.,]\d+)?', s)) >= 2 for s in sample):
                pair_cols.append(c)
        pair_cols = [c for c in pair_cols if 'unnamed' not in c.lower()]

    if not pair_cols:
        raise ValueError(
            f"Não encontrei colunas lat/lng nem colunas de par em {path}.\nColunas: {list(df.columns)}"
        )

    rows = []
    name_col = name_col or next((c for c in df.columns if 'nome' in c.lower() or 'empreendimento' in c.lower()), None)
    for _, r in df.iterrows():
        base_name = r[name_col] if (name_col and name_col in r) else None
        for c in pair_cols:
            pair = _parse_latlng_cell(r.get(c))
            if pair:
                lat, lng = pair
                rows.append({
                    "latitude": lat,
                    "longitude": lng,
                    "name": base_name if pd.notna(base_name) else None,
                    "source_col": c
                })

    if not rows:
        raise ValueError(f"Não foi possível extrair nenhum par lat/lng a partir de {pair_cols}.")

    return pd.DataFrame(rows, columns=["latitude", "longitude", "name", "source_col"])

# --------- runner principal ----------
def run_batch(input_path: str, sleep_sec: float, max_rows: int | None,
              types_csv: str | None, skip_existing: bool,
              pair_cols: list[str] | None):

    os.makedirs(RESULTS_DIR, exist_ok=True)

    api_key = get_api_key()
    if not api_key:
        raise SystemExit("API Key não encontrada em system/api_key.txt")

    # lê a planilha (suporta colunas-par '(Lat, Long)' e lat/lng separados)
    df_coords = read_coords_table(input_path, pair_cols_filter=pair_cols)

    # resolve as tipologias: ou as do usuário, ou todas do setup.interest_zones
    tipos = resolve_types(types_csv, interest_zones)
    print(f"Tipos a processar ({len(tipos)}): {', '.join(tipos)}")

    total_rows = len(df_coords) if max_rows is None else min(max_rows, len(df_coords))
    print(f"Coordenadas a processar: {total_rows} (de {len(df_coords)} extraídas)")

    for i, row in df_coords.head(total_rows).iterrows():
        lat = float(row["latitude"])
        lng = float(row["longitude"])
        label = row.get("name") or row.get("source_col") or f"{lat},{lng}"
        print(f"\n▶ Coordenada {i+1}/{total_rows}: {label} ({lat}, {lng})")

        for t in tipos:
            out_name = make_csv_filename(t, lat, lng)
            existing = glob(os.path.join(RESULTS_DIR, "**", out_name), recursive=True)
            if skip_existing and existing:
                print(f"  [skip] {out_name} já existe em {os.path.relpath(existing[0], RESULTS_DIR)}")
                continue

            print(f"  [go ] {t} .", end="", flush=True)
            try:
                saved_path = search_places(lat, lng, t, api_key=api_key)
                if saved_path:
                    # tenta descobrir UF e Região a partir do CSV
                    uf, region = infer_region_from_csv(saved_path)
                    if region:
                        new_path = move_to_region_folder(saved_path, region)
                        print(f" ok -> {os.path.basename(new_path)}  [{uf or '-'} / {region}]")
                    else:
                        print(f" ok -> {os.path.basename(saved_path)}  [região não identificada]")
                else:
                    print(" sem retorno")
            except Exception as e:
                print(f" ERRO: {e}")

            if sleep_sec > 0:
                time.sleep(sleep_sec)

    print("\n✅ Finalizado. Planilhas em:", os.path.abspath(RESULTS_DIR))

# --------- CLI ---------
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Runner para testar search_places em lote (todas as tipologias).")
    p.add_argument("-f", "--file", "--input", dest="input",
                   default=os.path.join("input", "Coordenadas_API_novastipologias (1).xlsx"),
                   help="Planilha com coordenadas (CSV ; ou Excel).")
    p.add_argument("--sleep", type=float, default=0.3, help="Pausa entre chamadas (segundos).")
    p.add_argument("--max-rows", type=int, default=None, help="Limitar número de coordenadas processadas.")
    p.add_argument("--types", type=str, default=None,
                   help="Filtrar tipos (ex.: 'school,hospital,restaurant'). Aceita rótulos do setup (ex.: 'cinema').")
    p.add_argument("--no-skip", action="store_true", help="Não pular arquivos já existentes.")
    p.add_argument("--pair-cols", type=str, default=None,
                   help="Restrinja às colunas-par informadas (ex.: \"Centro da Cidade (Lat, Long),'Bairro Estratégico (Lat, Long)'\").")
    args = p.parse_args()

    pair_cols = None
    if args.pair_cols:
        # aceita lista separada por vírgula (respeita nomes com espaços/acentos)
        pair_cols = [c.strip(" '\"") for c in args.pair_cols.split(",") if c.strip(" '\"")]

    run_batch(
        input_path=args.input,
        sleep_sec=args.sleep,
        max_rows=args.max_rows,
        types_csv=args.types,
        skip_existing=not args.no_skip,
        pair_cols=pair_cols
    )
