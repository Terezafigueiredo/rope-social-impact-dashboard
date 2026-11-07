"""Regras de privacidade aplicadas antes de publicar qualquer número.

Recebe agregados internos (que nunca vão para o site) e devolve somente o que
pode ser publicado em js/dados.js. `validar()` confere o resultado e é chamada
automaticamente por preparar_dados.py antes de gravar o arquivo.

Regras
1. Estado com menos de LIMITE_DETALHE sonhos ("restrito"): publica apenas o
   total, ou só "menos de LIMITE_DETALHE" se MASCARAR_RESTRITOS for True.
2. Em cada estado detalhado, categorias com menos de LIMITE_CELULA registros
   são somadas num grupo "outros". Faixa etária e sexo não têm grupo "outros":
   se alguma faixa ficar entre 1 e LIMITE_CELULA - 1, a distribuição inteira é
   omitida naquele estado.
3. Os detalhes do Brasil são a SOMA EXATA do que foi publicado para os estados
   detalhados: Brasil menos estados dá zero em qualquer categoria.
4. Sonhos por ano e pessoas impactadas do Brasil só incluem os estados
   restritos se a diferença (Brasil menos detalhados) descrever um GRUPO:
   pelo menos LIMITE_CELULA sonhos, 2 ou mais estados, e nenhum ano que possa
   ser atribuído a um estado restrito específico (limites de Fréchet).
   Caso contrário, os anos do Brasil viram a soma dos estados detalhados.
5. Parceiros só aparecem pelo nome se estiverem na lista autorizada.
6. Com totais mascarados, a soma do grupo restrito não pode permitir deduzir
   o total de nenhum estado (ex.: 3 estados somando 3 => todos têm 1).
7. Atualizações: um estado detalhado não pode ganhar entre 1 e LIMITE_CELULA - 1
   sonhos entre duas publicações (comparar as versões revelaria os novos casos).
"""
from collections import Counter

LIMITE_DETALHE = 10
LIMITE_CELULA = 5
MASCARAR_RESTRITOS = True  # estados restritos mostram "menos de 10" em vez do total exato

FAIXAS = ['Até 18', '19 a 40', '41 a 70', '71 ou mais']
SEXOS = ['Mulheres', 'Homens']
INDIVIDUAL = 'Indicação individual'
OUTROS = {'cats': 'Outros tipos', 'ills': 'Outras', 'partners': 'Outras origens'}
CAMPOS_RESTRITO = {'total', 'restrito'}
CAMPOS_RESTRITO_MASCARADO = {'restrito', 'totalMax'}
DIMENSOES_LISTA = ('cats', 'ills', 'partners')
DIMENSOES_FIXAS = {'bands': FAIXAS, 'sex': SEXOS}


class ErroPrivacidade(Exception):
    """Os dados não podem ser publicados com segurança."""


def agrupar_pequenos(contagem, rotulo, limite=LIMITE_CELULA):
    """Mantém as categorias com pelo menos `limite` registros e soma o resto em `rotulo`.
    O grupo de resto vem sempre por último."""
    visiveis, resto = [], 0
    for nome, n in contagem.items():
        if n <= 0:
            continue
        if n >= limite and nome != rotulo:
            visiveis.append([nome, n])
        else:
            resto += n
    visiveis.sort(key=lambda x: (-x[1], x[0]))
    if resto:
        visiveis.append([rotulo, resto])
    return visiveis


def distribuicao_fixa(contagem, chaves, limite=LIMITE_CELULA):
    """Faixas fixas (idade, sexo): omite tudo se alguma faixa for pequena demais."""
    valores = {k: int(contagem.get(k, 0)) for k in chaves}
    if any(0 < v < limite for v in valores.values()):
        return None
    return valores


def _media_idade(b):
    if b.get('ageSum') is not None and b.get('ageN'):
        return round(b['ageSum'] / b['ageN'])
    return b.get('ageAvg')  # média já arredondada do próprio grupo (modo de transição)


def publicar_estado(b, autorizados):
    parceiros = Counter()
    for nome, n in b['partners'].items():
        parceiros[nome if (nome in autorizados or nome == INDIVIDUAL) else OUTROS['partners']] += n
    bands = distribuicao_fixa(b['bands'], FAIXAS)
    sex = distribuicao_fixa(b['sex'], SEXOS)
    anos = {str(a): int(n) for a, n in sorted(b['years'].items(), key=lambda x: int(x[0]))}
    return {
        'total': b['total'],
        'years': anos,
        'cats': agrupar_pequenos(b['cats'], OUTROS['cats']),
        'ills': agrupar_pequenos(b['ills'], OUTROS['ills']),
        'partners': agrupar_pequenos(parceiros, OUTROS['partners']),
        'partnersN': len({k for k in b['partners'] if k != INDIVIDUAL}),
        'bands': bands,
        'sex': sex,
        'ageAvg': _media_idade(b) if bands is not None and b.get('ageN', 0) >= LIMITE_CELULA else None,
        'kids': bands['Até 18'] if bands is not None else None,
        'impact': int(b['impact']),
        'impactN': b['impactN'],
        'first': int(min(anos, key=int)),
        'last': int(max(anos, key=int)),
    }


def _somar_listas(listas, rotulo):
    c = Counter()
    for lista in listas:
        for nome, n in lista:
            c[nome] += n
    nomeados = sorted(([k, v] for k, v in c.items() if k != rotulo), key=lambda x: (-x[1], x[0]))
    return nomeados + ([[rotulo, c[rotulo]]] if c.get(rotulo) else [])


def _somar_dicts(dicts, chaves):
    return {k: sum(d[k] for d in dicts) for k in chaves}


# ---------- ataques por inferência (usados na geração e na validação) ----------

def intervalo_totais(n_estados, soma, limite=LIMITE_DETALHE):
    """Faixa possível do total de CADA estado restrito quando só se sabe que todos
    têm entre 1 e limite-1 sonhos e que, juntos, somam `soma`."""
    return max(1, soma - (n_estados - 1) * (limite - 1)), min(limite - 1, soma - (n_estados - 1))


def anos_atribuiveis(residuo_anos, totais_restritos, limite=LIMITE_DETALHE, sem_uf=0):
    """Limites de Fréchet: para cada estado restrito, os anos em que ele
    obrigatoriamente teve sonhos, dado o que é público.
    residuo_anos: {ano: n} = anos do Brasil menos anos dos estados detalhados.
    totais_restritos: {UF: total exato} ou {UF: None} (total mascarado).
    sem_uf: sonhos sem estado identificado (total público, também estão no resíduo)."""
    T = sum(residuo_anos.values())
    if not T:
        return {}
    n = len(totais_restritos)
    tmin_mascarado = intervalo_totais(n, T - sem_uf, limite)[0] if n else 0
    achados = {}
    for uf, t in totais_restritos.items():
        t_min = t if t is not None else tmin_mascarado
        forcados = {a: r + t_min - T for a, r in residuo_anos.items() if r + t_min - T > 0}
        if forcados:
            achados[uf] = forcados
    return achados


def _residuo_anos(br_anos, detalhados):
    soma = Counter()
    for d in detalhados:
        soma.update({str(a): n for a, n in d['years'].items()})
    return {a: n for a, n in (Counter({str(a): n for a, n in br_anos.items()}) - soma).items() if n}


def publicar(grupos, brasil, autorizados=frozenset(), mascarar=None, sem_uf=0):
    """grupos: {UF: agregado interno}; brasil: agregado interno de todos os registros
    (inclusive os `sem_uf` sonhos sem estado identificado, que nunca são atribuídos a um estado)."""
    mascarar = MASCARAR_RESTRITOS if mascarar is None else mascarar
    detalhados = sorted(u for u, b in grupos.items() if b['total'] >= LIMITE_DETALHE)
    restritos = sorted(u for u in grupos if u not in detalhados)
    pub = {u: publicar_estado(grupos[u], autorizados) for u in detalhados}
    est = [pub[u] for u in detalhados]
    n_restritos = sum(grupos[u]['total'] for u in restritos)

    if mascarar and restritos:
        lo, hi = intervalo_totais(len(restritos), n_restritos)
        if len(restritos) < 2 or lo == hi:
            raise ErroPrivacidade('Com os totais mascarados, o total dos estados restritos ainda poderia '
                                  'ser deduzido pela soma do Brasil. Revise a configuração antes de publicar.')

    com_faixas = [e for e in est if e['bands'] is not None]
    com_sexo = [e for e in est if e['sex'] is not None]
    br = {'total': brasil['total']}
    br['cats'] = _somar_listas([e['cats'] for e in est], OUTROS['cats'])
    br['ills'] = _somar_listas([e['ills'] for e in est], OUTROS['ills'])
    br['partners'] = _somar_listas([e['partners'] for e in est], OUTROS['partners'])
    nomes = set()
    for u in detalhados:
        nomes |= {k for k in grupos[u]['partners'] if k != INDIVIDUAL}
    br['partnersN'] = len(nomes)
    br['bands'] = _somar_dicts([e['bands'] for e in com_faixas], FAIXAS) if com_faixas else None
    br['sex'] = _somar_dicts([e['sex'] for e in com_sexo], SEXOS) if com_sexo else None
    br['kids'] = br['bands']['Até 18'] if br['bands'] else None
    origem_idade = [grupos[u] for u in detalhados if pub[u]['ageAvg'] is not None]
    if origem_idade and all(g.get('ageSum') is not None for g in origem_idade):
        br['ageAvg'] = round(sum(g['ageSum'] for g in origem_idade) / sum(g['ageN'] for g in origem_idade))
    else:
        br['ageAvg'] = None  # sem as somas exatas não dá para calcular sem inventar
    br['detalheN'] = sum(e['total'] for e in est)
    br['detalheUFs'] = len(detalhados)
    br['semUF'] = int(sem_uf)
    if sum(grupos[u]['total'] for u in grupos) + sem_uf != brasil['total']:
        raise ErroPrivacidade('A soma dos estados e dos sonhos sem estado não bate com o total do Brasil.')

    # Impacto (um único número): basta que a diferença descreva um grupo.
    grupo_ok = not restritos or (n_restritos + sem_uf >= LIMITE_CELULA and len(restritos) >= 2)
    if grupo_ok:
        br['impact'], br['impactN'] = int(brasil['impact']), brasil['impactN']
    else:
        br['impact'] = sum(e['impact'] for e in est)
        br['impactN'] = sum(e['impactN'] for e in est)
    # Anos: além do grupo, nenhum ano pode ser atribuído a um estado restrito.
    anos_ok = grupo_ok
    if anos_ok and restritos:
        residuo = _residuo_anos(brasil['years'], est)
        totais_publicos = {u: (None if mascarar else grupos[u]['total']) for u in restritos}
        anos_ok = not anos_atribuiveis(residuo, totais_publicos, sem_uf=sem_uf)
    if anos_ok:
        anos = {str(a): int(n) for a, n in brasil['years'].items()}
    else:
        anos = {}
        for e in est:
            for a, n in e['years'].items():
                anos[a] = anos.get(a, 0) + n
    br['years'] = {a: anos[a] for a in sorted(anos, key=int)}
    br['first'], br['last'] = int(min(anos, key=int)), int(max(anos, key=int))
    br['anosIncluemRestritos'] = bool(restritos) and anos_ok

    saida = {'BR': br}
    saida.update(pub)
    for u in restritos:
        saida[u] = ({'restrito': True, 'totalMax': LIMITE_DETALHE - 1} if mascarar
                    else {'total': grupos[u]['total'], 'restrito': True})
    return saida


# ---------- validação automática do que vai ser publicado ----------

def validar(saida, autorizados=frozenset()):
    """Confere o resultado de publicar(). Devolve a lista de problemas (vazia = ok).
    As mensagens nunca incluem os valores que poderiam ser recuperados."""
    erros = []
    br = saida['BR']
    ufs = {u: d for u, d in saida.items() if u != 'BR'}
    det = {u: d for u, d in ufs.items() if not d.get('restrito')}
    res = {u: d for u, d in ufs.items() if d.get('restrito')}
    mascarado = any('totalMax' in d for d in res.values())

    for u, d in res.items():
        if set(d) not in (CAMPOS_RESTRITO, CAMPOS_RESTRITO_MASCARADO):
            erros.append(f'{u}: estado restrito publica campos além do total')
        elif 'total' in d and d['total'] >= LIMITE_DETALHE:
            erros.append(f'{u}: marcado como restrito com total acima do limite')
    if mascarado and any('total' in d for d in res.values()):
        erros.append('mistura de totais exatos e mascarados entre estados restritos')
    for u, d in det.items():
        if d['total'] < LIMITE_DETALHE:
            erros.append(f'{u}: estado detalhado com menos de {LIMITE_DETALHE} sonhos')

    rotulos = set(OUTROS.values())
    for u, d in [('BR', br), *det.items()]:
        for dim in DIMENSOES_LISTA:
            for nome, n in d[dim]:
                if nome not in rotulos and n < LIMITE_CELULA:
                    erros.append(f'{u}.{dim}: categoria com menos de {LIMITE_CELULA} pessoas')
                if dim == 'partners' and nome not in autorizados | {INDIVIDUAL, OUTROS['partners']}:
                    erros.append(f'{u}: parceiro fora da lista autorizada')
        for dim in DIMENSOES_FIXAS:
            for n in (d.get(dim) or {}).values():
                if 0 < n < LIMITE_CELULA:
                    erros.append(f'{u}.{dim}: faixa com menos de {LIMITE_CELULA} pessoas')

    for dim in DIMENSOES_LISTA:
        soma = Counter()
        for d in det.values():
            soma.update(dict(d[dim]))
        if Counter(dict(br[dim])) != soma:
            erros.append(f'{dim}: Brasil menos estados detalhados revela diferença')
    for dim, chaves in DIMENSOES_FIXAS.items():
        com = [d[dim] for d in det.values() if d.get(dim) is not None]
        esperado = _somar_dicts(com, chaves) if com else None
        if br.get(dim) != esperado:
            erros.append(f'{dim}: Brasil menos estados detalhados revela diferença')

    total_det = sum(d['total'] for d in det.values())
    sem_uf = br.get('semUF', 0)
    if br.get('detalheN') != total_det:
        erros.append('detalheN não bate com os estados detalhados')
    if not isinstance(sem_uf, int) or sem_uf < 0 or sem_uf > br['total'] - total_det:
        erros.append('semUF inválido')
    if res:
        soma_res = br['total'] - total_det - sem_uf
        if mascarado:
            lo, hi = intervalo_totais(len(res), soma_res)
            if len(res) < 2 or lo == hi:
                erros.append('total mascarado pode ser deduzido pela soma do Brasil')
        elif soma_res != sum(d['total'] for d in res.values()):
            erros.append('soma dos estados não bate com o total do Brasil')
        residuo = _residuo_anos(br['years'], det.values())
        if residuo:
            if len(res) < 2 or sum(residuo.values()) < LIMITE_CELULA:
                erros.append('anos do Brasil permitem isolar um estado restrito')
            totais = {u: d.get('total') for u, d in res.items()}
            if anos_atribuiveis(residuo, totais, sem_uf=sem_uf):
                erros.append('anos do Brasil permitem atribuir sonhos a um estado restrito')
    return erros


def validar_atualizacao(anterior, nova):
    """Compara com a versão já publicada: pequenas variações revelariam os casos novos."""
    if not anterior:
        return []
    erros = []
    for u, d in nova.items():
        a = anterior.get(u)
        if not a or d.get('restrito') or a.get('restrito'):
            continue
        base_a = a.get('detalheN', a.get('total')) if u == 'BR' else a.get('total')
        base_n = d.get('detalheN', d.get('total')) if u == 'BR' else d.get('total')
        if base_a is not None and base_n is not None and 0 < abs(base_n - base_a) < LIMITE_CELULA:
            erros.append(f'{u}: variação de menos de {LIMITE_CELULA} sonhos desde a última publicação')
    return erros


def ler_autorizados(caminho):
    """Lê a lista de parceiros autorizados (uma por linha; # inicia comentário)."""
    try:
        linhas = caminho.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return frozenset()
    return frozenset(l.split('#', 1)[0].strip() for l in linhas if l.split('#', 1)[0].strip())
