# region_utils.py
import os
import pandas as pd

UF_TO_REGION = {
    # Norte
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    # Nordeste
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    # Centro-Oeste
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    # Sudeste
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    # Sul
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

def uf_from_city_state(city_state: str) -> str | None:
    if not isinstance(city_state, str) or "/" not in city_state:
        return None
    uf = city_state.split("/")[-1].strip().upper()
    return uf if uf in UF_TO_REGION else None

def region_from_uf(uf: str | None) -> str | None:
    if not uf:
        return None
    return UF_TO_REGION.get(uf)

def infer_region_from_csv(csv_path: str) -> tuple[str | None, str | None]:
    """
    Lê o CSV salvo pelo search_places, pega city_state do 1º registro,
    devolve (UF, Região). Se não achar, retorna (None, None).
    """
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
        if "city_state" not in df.columns or df.empty:
            return None, None
        uf = uf_from_city_state(str(df.iloc[0]["city_state"]))
        return uf, region_from_uf(uf)
    except Exception:
        return None, None

def move_to_region_folder(csv_path: str, region: str) -> str:
    """
    Move o arquivo para system/results/<REGIÃO>/ mantendo o mesmo nome.
    Retorna o caminho novo.
    """
    base_dir, fname = os.path.split(csv_path)
    target = os.path.join(base_dir, region)
    os.makedirs(target, exist_ok=True)
    new_path = os.path.join(target, fname)
    if os.path.abspath(csv_path) != os.path.abspath(new_path):
        try:
            os.replace(csv_path, new_path)
        except FileNotFoundError:
            # Se o arquivo não existir por algum motivo, apenas retorna o caminho original
            return csv_path
    return new_path
