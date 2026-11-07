"""Gera js/dados.js a partir da planilha, aplicando as regras de scripts/privacidade.py.

Uso:  python scripts/preparar_dados.py planilha.xlsx js/dados.js
Depois: python -m unittest discover -s tests

Arquivos LOCAIS necessários (fora do Git):
  scripts/regras_classificacao.json    palavras-chave de classificação (modelo: regras_classificacao.exemplo.json)
  scripts/indicacoes_individuais.txt   nomes de pessoas físicas que indicam sonhos (opcional)

Segurança: o arquivo só é gravado se privacidade.validar() e
privacidade.validar_atualizacao() não encontrarem nenhum problema.
"""
import json, re, unicodedata, collections, datetime, sys, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import privacidade as P

AQUI = pathlib.Path(__file__).parent
def norm(s): return unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().strip()

REGRAS = None
PESSOAS = []
def carregar_regras(caminho=AQUI/'regras_classificacao.json', pessoas=AQUI/'indicacoes_individuais.txt'):
    """As palavras-chave vêm das descrições e diagnósticos reais, por isso ficam num arquivo local."""
    global REGRAS, PESSOAS
    if not pathlib.Path(caminho).exists():
        sys.exit(f'Falta {caminho}. Copie regras_classificacao.exemplo.json e preencha (o arquivo fica fora do Git).')
    REGRAS = json.loads(pathlib.Path(caminho).read_text(encoding='utf-8'))
    p = pathlib.Path(pessoas)
    PESSOAS = [norm(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()] if p.exists() else []
    if not p.exists():
        print(f'AVISO: {p.name} não encontrado. Indicações de pessoas físicas não serão reconhecidas como '
              '"Indicação individual" (ficam sem estado e fora da lista autorizada). Confira antes de publicar.')

def palavra_que_casa(n, r):
    """Qual condição da regra classificou o texto (None se nenhuma). Usado também na revisão."""
    if n in r.get('igual', []): return '=' + n
    for k in r.get('comeca', []):
        if n.startswith(k): return k
    for k in r.get('contem', []):
        if k in n: return k
    if r.get('regex'):
        m = re.search(r['regex'], n)
        if m: return m.group(0)
    if r.get('pessoas'):
        for k in PESSOAS:
            if k in n: return '(pessoa física)'
    return None

def casa(n, r):
    return palavra_que_casa(n, r) is not None

def uf(c):
    """UF pela origem: palavras-chave da cidade/instituição ou lista explícita de origens por UF.
    Origem desconhecida -> None (sem estado identificado). Nunca atribui um estado por padrão."""
    n=norm(c)
    for r in REGRAS['uf']:
        if casa(n, r): return r['uf']
    origem=partner(c)
    for sigla, origens in REGRAS.get('uf_por_origem', {}).items():
        if origem in origens: return sigla
    return REGRAS.get('uf_padrao')

# Sexo: só valores reconhecidos. Vazio ou desconhecido = não informado (fica fora da distribuição).
SEXO = {'h': 'Homens', 'homem': 'Homens', 'masculino': 'Homens',
        'm': 'Mulheres', 'f': 'Mulheres', 'mulher': 'Mulheres', 'feminino': 'Mulheres'}
def sexo(v):
    return SEXO.get(norm(v))
def partner(c):
    n=norm(c)
    for r in REGRAS['parceiros']:
        if casa(n, r): return r['nome']
    return str(c).strip()  # nome bruto: só é publicado se estiver na lista autorizada
def cat(s):
    n=(s or '').lower()
    for r in REGRAS['tipos']:
        if casa(n, r): return r['nome']
    return REGRAS['tipo_padrao']
def ill(s):
    n=norm(s)
    if not n: return None
    for r in REGRAS['saude']:
        if casa(n, r): return r['nome']
    return REGRAS['saude_padrao']
def band(a):
    if a is None: return None
    return 'Até 18' if a<=18 else '19 a 40' if a<=40 else '41 a 70' if a<=70 else '71 ou mais'

def ler_linhas(caminho):
    import openpyxl
    ws=openpyxl.load_workbook(caminho,data_only=True)['sonhos']
    rows=[]
    for r in ws.iter_rows(min_row=6,values_only=True):
        if not isinstance(r[0],(int,float)) or not r[1]: continue
        d=r[6]
        if isinstance(d,datetime.datetime): y=d.year
        else: y=int(re.findall(r'(20\d\d)',str(d))[0])
        age=r[4] if isinstance(r[4],(int,float)) else None
        imp=r[11] if isinstance(r[11],(int,float)) else None
        rows.append(dict(uf=uf(r[5]),p=partner(r[5]),y=y,age=age,sex=sexo(r[2]),c=cat(r[7]),i=ill(r[8]),imp=imp,
                         _linha=r[0],_bruto={'sexo':r[2],'origem':r[5],'sonho':r[7],'saude':r[8]}))
    return rows

def revisar(rows, destino, autorizados=frozenset()):
    """Relatório LOCAL para conferir a classificação com a planilha (contém textos da planilha:
    *.csv está no .gitignore e o arquivo nunca deve ser publicado). Lista só o que merece revisão."""
    import csv
    suspeitas=[]
    def no_meio(n, k):  # palavra-chave curta ou que casou no meio de outra palavra (ex.: 'time' em 'sentimento')
        i=n.find(k)
        return i>0 and n[i-1].isalnum() or (len(k)<=4 and i+len(k)<len(n) and n[i+len(k)].isalnum())
    for x in rows:
        b=x['_bruto']
        if x['sex'] is None: suspeitas.append((x['_linha'],'sexo',b['sexo'],'não informado','','valor não reconhecido'))
        if x['uf'] is None: suspeitas.append((x['_linha'],'uf',b['origem'],'sem estado','','origem fora das listas'))
        if x['p']==str(b['origem'] or '').strip() and x['p'] not in autorizados:
            suspeitas.append((x['_linha'],'parceiro',b['origem'],x['p'],'','nome bruto (não publicado)'))
        for campo,regras,texto,norm_fn in (('tipo',REGRAS['tipos'],b['sonho'],lambda s:(s or '').lower()),
                                          ('saude',REGRAS['saude'],b['saude'],norm)):
            n=norm_fn(texto)
            k=next((palavra_que_casa(n,r) for r in regras if palavra_que_casa(n,r)),None)
            classe=x['c'] if campo=='tipo' else x['i']
            if k is None and classe is not None:
                suspeitas.append((x['_linha'],campo,texto,classe,'','categoria padrão (nenhuma palavra-chave)'))
            elif k and not k.startswith('=') and no_meio(n,k):
                suspeitas.append((x['_linha'],campo,texto,classe,k,'palavra-chave dentro de outra palavra'))
    with open(destino,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f,delimiter=';'); w.writerow('linha;campo;valor_original;classificacao;palavra_chave;motivo'.split(';')); w.writerows(suspeitas)
    return collections.Counter((c,m) for _,c,_,_,_,m in suspeitas)

def agregar(rs):
    """Agregado INTERNO (contagens e somas). Nunca é publicado diretamente."""
    C=lambda f: dict(collections.Counter(x[f] for x in rs if x[f] is not None))
    ages=[x['age'] for x in rs if x['age'] is not None]
    imps=[x['imp'] for x in rs if x['imp'] is not None]
    return dict(total=len(rs),years=C('y'),cats=C('c'),ills=C('i'),partners=C('p'),
      bands=dict(collections.Counter(band(a) for a in ages)),sex=C('sex'),
      ageSum=sum(ages),ageN=len(ages),impact=int(sum(imps)),impactN=len(imps))

def ler_publicado(destino):
    """Versão já publicada (para comparar e evitar a dedução por diferença entre versões)."""
    try:
        t=pathlib.Path(destino).read_text(encoding='utf-8')
        return json.loads(re.search(r'window\.DADOS = (\{.*?\});\n',t,re.S).group(1))
    except (FileNotFoundError, AttributeError, ValueError):
        return None

def escrever(destino, saida):
    meta={'gerado':datetime.date.today().isoformat(),'limiteDetalhe':P.LIMITE_DETALHE,
          'limiteCelula':P.LIMITE_CELULA,'fonte':'Planilha Sonhos Realizados (Instituto ROPE)'}
    texto=('// Gerado por scripts/preparar_dados.py. Somente dados agregados, após as regras de scripts/privacidade.py.\n'
           'window.DADOS = '+json.dumps(saida,ensure_ascii=False)+';\n'
           'window.DADOS_META = '+json.dumps(meta,ensure_ascii=False)+';\n')
    tmp=pathlib.Path(str(destino)+'.tmp')
    tmp.write_text(texto,encoding='utf-8')
    os.replace(tmp,destino)  # escrita atômica: nunca fica um arquivo pela metade

def gerar(planilha, destino, autorizados=None, forcar_atualizacao=False, revisao=None):
    if REGRAS is None: carregar_regras()
    autorizados=P.ler_autorizados(AQUI/'parceiros_autorizados.txt') if autorizados is None else autorizados
    rows=ler_linhas(planilha)
    if revisao:
        for (campo,motivo),n in sorted(revisar(rows,revisao,autorizados).items()): print(f'revisar {campo}: {n} ({motivo})')
    # Sem estado identificado: conta no total do Brasil, nunca é atribuído a um estado
    grupos={u:agregar([x for x in rows if x['uf']==u]) for u in sorted({x['uf'] for x in rows if x['uf']})}
    sem_uf=sum(1 for x in rows if not x['uf'])
    try:
        saida=P.publicar(grupos,agregar(rows),autorizados,sem_uf=sem_uf)
    except P.ErroPrivacidade as e:
        sys.exit(f'NADA FOI GRAVADO. {e}')
    problemas=P.validar(saida,autorizados)
    if not forcar_atualizacao:
        problemas+=P.validar_atualizacao(ler_publicado(destino),saida)
    if problemas:
        sys.exit('NADA FOI GRAVADO. Problemas de privacidade:\n- '+'\n- '.join(problemas))
    escrever(destino,saida)
    return saida

if __name__=='__main__':
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args)!=2 or not args[1].endswith('.js'):
        sys.exit('Uso: python scripts/preparar_dados.py planilha.xlsx js/dados.js [--primeira-publicacao] [--revisao]')
    # --primeira-publicacao: ignora a comparação com a versão anterior (use só ao recriar o repositório)
    # --revisao: grava scripts/revisao_classificacao.csv (LOCAL, fora do Git) com o que merece conferência
    saida=gerar(args[0],args[1],forcar_atualizacao='--primeira-publicacao' in sys.argv,
                revisao=AQUI/'revisao_classificacao.csv' if '--revisao' in sys.argv else None)
    for k,v in saida.items(): print(k,'restrito' if v.get('restrito') else v['total'])
