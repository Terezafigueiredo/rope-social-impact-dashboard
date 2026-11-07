"""Gera js/mapa-ufs.js (contornos dos estados) a partir da malha territorial do IBGE.

Fonte: API de Malhas do IBGE (dados públicos; citar a fonte).
  https://servicodados.ibge.gov.br/api/v4/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF

Uso:
  curl -o malha_uf.json "<URL acima>"
  python scripts/preparar_mapa.py malha_uf.json js/mapa-ufs.js

A saída contém somente siglas de UF e coordenadas numéricas (validadas), para que
o site não precise executar nenhum script de terceiros.
"""
import json, math, pathlib, sys

# Código IBGE da UF -> sigla
CODIGOS = {'11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
           '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
           '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR', '42': 'SC', '43': 'RS',
           '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'}
CASAS = 3  # ~100 m: mais que suficiente para a escala do dashboard


def ponto(p):
    x, y = p[0], p[1]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)):
        raise ValueError('coordenada inválida')
    if not (-75 <= x <= -28 and -35 <= y <= 6):
        raise ValueError(f'coordenada fora do Brasil: {x}, {y}')
    return [round(x, CASAS), round(y, CASAS)]


def anel(r):
    saida = []
    for p in r:
        q = ponto(p)
        if not saida or saida[-1] != q:  # remove pontos repetidos após o arredondamento
            saida.append(q)
    return saida if len(saida) >= 4 else None  # ilhota que some no arredondamento


def converter(geo):
    feats = []
    for f in geo['features']:
        uf = CODIGOS[str(f['properties']['codarea'])]
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else None
        if polys is None:
            raise ValueError(f'geometria inesperada em {uf}')
        limpos = []
        for poly in polys:
            aneis = [anel(r) for r in poly]
            if aneis[0] is not None:  # sem contorno externo, o polígono inteiro é descartado
                limpos.append([a for a in aneis if a is not None])
        if not limpos:
            raise ValueError(f'{uf} ficou sem contorno')
        polys = limpos
        feats.append({'type': 'Feature', 'properties': {'uf': uf},
                      'geometry': {'type': 'MultiPolygon', 'coordinates': polys}})
    ufs = sorted(f['properties']['uf'] for f in feats)
    if ufs != sorted(CODIGOS.values()):
        raise ValueError('a malha precisa ter exatamente as 27 UFs')
    feats.sort(key=lambda f: f['properties']['uf'])
    return {'type': 'FeatureCollection', 'features': feats}


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Uso: python scripts/preparar_mapa.py malha_uf.json js/mapa-ufs.js')
    geo = converter(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')))
    texto = ('// Contornos das UFs: Malha territorial do IBGE (servicodados.ibge.gov.br), gerado por scripts/preparar_mapa.py.\n'
             'window.MAPA_UFS = ' + json.dumps(geo, separators=(',', ':')) + ';\n')
    pathlib.Path(sys.argv[2]).write_text(texto, encoding='utf-8')
    print(len(geo['features']), 'UFs,', len(texto) // 1024, 'KB')
