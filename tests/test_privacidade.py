"""Testes de privacidade e segurança do dashboard.

Rodar na raiz do projeto:  python -m unittest discover -s tests -v

A. O arquivo público (js/dados.js) não permite recuperar dados restritos
   por cálculo (subtração entre Brasil e estados) nem por inspeção do código.
B. Os arquivos que vão para o GitHub/GitHub Pages não expõem a base original,
   listas locais, segredos nem dependem de scripts de terceiros.
C. As regras de scripts/privacidade.py, testadas com cenários de teste
   FICTÍCIOS (existem só aqui, nunca são publicados).
"""
import json, pathlib, re, subprocess, sys, unicodedata, unittest
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))
import privacidade as P  # noqa: E402


def ler_dados():
    txt = (RAIZ / 'js' / 'dados.js').read_text(encoding='utf-8')
    dados = json.loads(re.search(r'window\.DADOS = (\{.*?\});\n', txt, re.S).group(1))
    meta = json.loads(re.search(r'window\.DADOS_META = (\{.*?\});', txt, re.S).group(1))
    return txt, dados, meta


def norm(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().strip()


def arquivos_publicos():
    """Arquivos versionados (o que vai para o GitHub). Sem git, usa a pasta inteira."""
    try:
        saida = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                               cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        return [RAIZ / l for l in saida.splitlines() if l.strip() and (RAIZ / l).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in RAIZ.rglob('*') if p.is_file() and '.git' not in p.parts]


DIMENSOES_LISTA = ('cats', 'ills', 'partners')
DIMENSOES_FIXAS = {'bands': P.FAIXAS, 'sex': P.SEXOS}
RESIDUAIS = set(P.OUTROS.values())


class A_ArquivoPublico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.txt, cls.dados, cls.meta = ler_dados()
        cls.br = cls.dados['BR']
        cls.ufs = {u: d for u, d in cls.dados.items() if u != 'BR'}
        cls.detalhados = {u: d for u, d in cls.ufs.items() if not d.get('restrito')}
        cls.restritos = {u: d for u, d in cls.ufs.items() if d.get('restrito')}
        cls.k = cls.meta.get('limiteCelula', P.LIMITE_CELULA)
        cls.kd = cls.meta.get('limiteDetalhe', P.LIMITE_DETALHE)

    def test_limites_publicados_batem_com_o_script(self):
        self.assertEqual(self.meta.get('limiteCelula'), P.LIMITE_CELULA)
        self.assertEqual(self.meta.get('limiteDetalhe'), P.LIMITE_DETALHE)

    def test_validador_automatico_aprova_o_arquivo(self):
        """O mesmo validador que o script roda antes de gravar."""
        autorizados = P.ler_autorizados(RAIZ / 'scripts' / 'parceiros_autorizados.txt')
        self.assertEqual(P.validar(self.dados, autorizados), [])

    def test_estado_restrito_publica_somente_o_total(self):
        for uf, d in self.restritos.items():
            self.assertIn(set(d), (P.CAMPOS_RESTRITO, P.CAMPOS_RESTRITO_MASCARADO), f'{uf} publica campos além do total')
            if 'total' in d:
                self.assertLess(d['total'], self.kd)
            else:
                self.assertEqual(d['totalMax'], self.kd - 1)

    def test_nenhum_ano_atribuivel_a_estado_restrito(self):
        """Limites de Fréchet, calculados aqui de forma independente do script:
        o mínimo de sonhos de um estado restrito num ano é max(0, r_ano + t_estado - T).
        Precisa ser 0 para todo estado e todo ano."""
        anos_det = Counter()
        for d in self.detalhados.values():
            anos_det.update(d['years'])
        residuo = Counter(self.br['years']) - anos_det
        T = sum(residuo.values())
        if not T:
            return
        n = len(self.restritos)
        sem_uf = self.br.get('semUF', 0)
        for uf, d in self.restritos.items():
            t_min = d['total'] if 'total' in d else max(1, (T - sem_uf) - (n - 1) * (self.kd - 1))
            atribuiveis = [a for a, r in residuo.items() if r + t_min - T > 0]
            self.assertEqual(len(atribuiveis), 0, f'{uf}: há ano(s) atribuível(is) por subtração')

    def test_total_mascarado_nao_pode_ser_deduzido(self):
        mascarados = [d for d in self.restritos.values() if 'totalMax' in d]
        if not mascarados:
            self.skipTest('totais exatos (MASCARAR_RESTRITOS = False)')
        self.assertEqual(len(mascarados), len(self.restritos), 'mistura de totais exatos e mascarados')
        soma = self.br['total'] - sum(d['total'] for d in self.detalhados.values()) - self.br.get('semUF', 0)
        n = len(mascarados)
        lo, hi = max(1, soma - (n - 1) * (self.kd - 1)), min(self.kd - 1, soma - (n - 1))
        self.assertGreaterEqual(n, 2)
        self.assertLess(lo, hi, 'a soma do Brasil determina o total de algum estado')

    def test_estado_pequeno_nunca_e_detalhado(self):
        for uf, d in self.detalhados.items():
            self.assertGreaterEqual(d['total'], self.kd, f'{uf} detalhado com poucos registros')

    def test_nenhuma_celula_pequena_com_nome(self):
        """Toda categoria nomeada tem pelo menos k pessoas; só os grupos 'outros' podem ser menores."""
        for uf, d in [('BR', self.br), *self.detalhados.items()]:
            for dim in DIMENSOES_LISTA:
                for nome, n in d[dim]:
                    if nome not in RESIDUAIS:
                        self.assertGreaterEqual(n, self.k, f'{uf}.{dim}: "{nome}" = {n}')
            for dim in DIMENSOES_FIXAS:
                if d.get(dim) is not None:
                    for nome, n in d[dim].items():
                        self.assertTrue(n == 0 or n >= self.k, f'{uf}.{dim}: "{nome}" = {n}')

    def test_ataque_por_subtracao_nao_revela_nada(self):
        """Brasil menos a soma dos estados detalhados deve dar ZERO em toda categoria sensível."""
        for dim in DIMENSOES_LISTA:
            soma = Counter()
            for d in self.detalhados.values():
                for nome, n in d[dim]:
                    soma[nome] += n
            # As mensagens nunca mostram os valores recuperados: um log de teste pode ser público.
            diferenca = (Counter(dict(self.br[dim])) - soma) + (soma - Counter(dict(self.br[dim])))
            self.assertTrue(not diferenca, f'{dim}: subtração Brasil − estados revela {len(diferenca)} categoria(s)')
        for dim, chaves in DIMENSOES_FIXAS.items():
            com = [d[dim] for d in self.detalhados.values() if d.get(dim) is not None]
            if self.br.get(dim) is None:
                self.assertEqual(com, [])
                continue
            for c in chaves:
                self.assertTrue(self.br[dim][c] == sum(x[c] for x in com), f'{dim}.{c}: subtração revela diferença')
        if self.br.get('kids') is not None:
            self.assertEqual(self.br['kids'], self.br['bands']['Até 18'])

    def test_diferenca_de_anos_e_impacto_so_descreve_grupo(self):
        """Se o Brasil inclui os restritos em anos/impacto, a diferença deve cobrir >= k sonhos em >= 2 estados."""
        anos_det = Counter()
        for d in self.detalhados.values():
            anos_det.update({a: n for a, n in d['years'].items()})
        diferenca = Counter(self.br['years']) - anos_det
        soma_restritos = self.br['total'] - sum(d['total'] for d in self.detalhados.values())
        if sum(diferenca.values()):  # anos do Brasil incluem os restritos
            self.assertGreaterEqual(len(self.restritos), 2, 'diferença de anos atribuível a um único estado')
            self.assertGreaterEqual(soma_restritos, self.k)
            self.assertEqual(sum(diferenca.values()), soma_restritos)
            self.assertTrue(self.br['anosIncluemRestritos'])
        else:
            self.assertFalse(self.br['anosIncluemRestritos'] and self.restritos)
        if self.br['impact'] != sum(d['impact'] for d in self.detalhados.values()):  # impacto inclui os restritos
            self.assertGreaterEqual(len(self.restritos), 2, 'diferença de impacto atribuível a um único estado')
            self.assertGreaterEqual(soma_restritos, self.k)

    def test_totais_consistentes(self):
        if all('total' in d for d in self.ufs.values()):
            self.assertEqual(self.br['total'], sum(d['total'] for d in self.ufs.values()) + self.br.get('semUF', 0))
        self.assertEqual(self.br['first'], int(min(self.br['years'], key=int)))
        self.assertEqual(self.br['last'], int(max(self.br['years'], key=int)))
        self.assertEqual(self.br['detalheN'], sum(d['total'] for d in self.detalhados.values()))
        self.assertEqual(sum(self.br['years'].values()),
                         self.br['total'] if self.br['anosIncluemRestritos'] else self.br['detalheN'])
        for uf, d in self.detalhados.items():
            for dim in ('cats', 'partners'):
                self.assertEqual(sum(n for _, n in d[dim]), d['total'], f'{uf}.{dim}')
            self.assertEqual(sum(d['years'].values()), d['total'], f'{uf}.years')

    def test_parceiros_somente_da_lista_autorizada(self):
        autorizados = P.ler_autorizados(RAIZ / 'scripts' / 'parceiros_autorizados.txt')
        for uf, d in [('BR', self.br), *self.detalhados.items()]:
            for nome, _ in d['partners']:
                self.assertIn(nome, autorizados | {P.INDIVIDUAL, P.OUTROS['partners']}, f'{uf}: "{nome}"')

    def test_inspecao_textos_e_campos_conhecidos(self):
        """Qualquer texto ou campo inesperado no arquivo público falha (ex.: nome solto, soma de idades)."""
        autorizados = P.ler_autorizados(RAIZ / 'scripts' / 'parceiros_autorizados.txt')
        cats = {'Mensagem de ídolo', 'Encontro com ídolo', 'Presentes e outros', 'Passeio', 'Festa ou celebração',
                'Estudos e criação', 'Experiência radical'}
        ills = {'Câncer', 'Neurológica', 'Cardíaca', 'Renal', 'Transplante', 'Outras'}
        permitidos = cats | ills | set(P.FAIXAS) | set(P.SEXOS) | autorizados | RESIDUAIS | {P.INDIVIDUAL}
        campos = {'total', 'restrito', 'years', 'cats', 'ills', 'partners', 'partnersN', 'bands', 'sex', 'ageAvg',
                  'kids', 'impact', 'impactN', 'first', 'last', 'detalheN', 'detalheUFs', 'anosIncluemRestritos', 'totalMax',
                  'semUF'}
        for uf, d in self.dados.items():
            self.assertTrue(uf == 'BR' or re.fullmatch(r'[A-Z]{2}', uf))
            self.assertLessEqual(set(d), campos, f'{uf}: campos inesperados {set(d) - campos}')
            for dim in DIMENSOES_LISTA:
                for nome, n in d.get(dim, []):
                    self.assertIn(nome, permitidos, f'{uf}.{dim}: texto inesperado "{nome}"')
                    self.assertIsInstance(n, int)
        self.assertLessEqual(set(self.meta), {'gerado', 'limiteDetalhe', 'limiteCelula', 'fonte'})
        sem_meta = self.txt.split('window.DADOS_META')[0]
        textos = set(re.findall(r'"([^"]*)"', sem_meta))
        desconhecidos = {t for t in textos if t not in permitidos | campos and not re.fullmatch(r'[A-Z]{2}|BR|\d{4}', t)}
        self.assertEqual(desconhecidos, set(), 'textos desconhecidos no arquivo público')

    def test_nomes_de_pessoas_fisicas_nao_aparecem(self):
        lista = RAIZ / 'scripts' / 'indicacoes_individuais.txt'
        if not lista.exists():
            self.skipTest('lista local de indicações individuais não está nesta máquina')
        nomes = [norm(l) for l in lista.read_text(encoding='utf-8').splitlines() if l.strip()]
        for arq in arquivos_publicos():
            if arq.suffix in {'.js', '.html', '.md', '.css', '.py', '.txt'} and arq != lista:
                conteudo = norm(arq.read_text(encoding='utf-8', errors='ignore'))
                for n in nomes:
                    self.assertNotIn(n, conteudo, f'nome da lista local aparece em {arq.name}')


class B_ArquivosDoRepositorio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.publicos = arquivos_publicos()
        cls.rel = [p.relative_to(RAIZ).as_posix() for p in cls.publicos]

    def test_base_original_e_listas_locais_fora_do_git(self):
        proibidos = re.compile(r'\.(xlsx|xls|xlsm|csv|ods|sqlite|db)$|(^|/)dados\.json$|indicacoes_individuais\.txt$', re.I)
        self.assertEqual([r for r in self.rel if proibidos.search(r)], [])
        gi = (RAIZ / '.gitignore').read_text(encoding='utf-8')
        for padrao in ('*.xlsx', '*.csv', 'scripts/indicacoes_individuais.txt'):
            self.assertIn(padrao, gi)

    def test_dados_somente_em_dados_js(self):
        """Nenhum outro arquivo público carrega estrutura de dados dos sonhos."""
        for p, r in zip(self.publicos, self.rel):
            if p.suffix == '.js' and r != 'js/dados.js':
                t = p.read_text(encoding='utf-8')
                self.assertNotRegex(t, r'window\.DADOS\s*=', r)
                self.assertNotRegex(t, r'"(impact|ageAvg|ills|partners)"\s*:', r)

    def test_mapa_local_contem_apenas_ufs_e_numeros(self):
        t = (RAIZ / 'js' / 'mapa-ufs.js').read_text(encoding='utf-8')
        corpo = re.search(r'window\.MAPA_UFS = (\{.*\});', t, re.S).group(1)
        geo = json.loads(corpo)
        self.assertEqual(sorted(f['properties']['uf'] for f in geo['features']), sorted(set(
            f['properties']['uf'] for f in geo['features'])))
        self.assertEqual(len(geo['features']), 27)
        textos = set(re.findall(r'"([^"]*)"', corpo))
        self.assertLessEqual(textos, {'type', 'FeatureCollection', 'Feature', 'properties', 'uf', 'geometry',
                                      'MultiPolygon', 'coordinates', 'features'} | {f['properties']['uf'] for f in geo['features']})

    def test_sem_scripts_de_terceiros(self):
        html = (RAIZ / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'<script[^>]+src="(https?:)?//', html), [], 'script externo no HTML')
        for p, r in zip(self.publicos, self.rel):
            if p.suffix == '.js':
                t = p.read_text(encoding='utf-8')
                self.assertNotRegex(t, r'createElement\(\s*[\'"]script', f'{r} injeta script')
                self.assertNotRegex(t, r'https?://(cdn\.jsdelivr|unpkg|cdnjs)', f'{r} usa CDN')

    def test_sem_segredos(self):
        padrao = re.compile(r'(api[_-]?key|secret|passw(or)?d|senha|token|bearer)\s*[:=]\s*["\'][^"\']{6,}'
                            r'|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY', re.I)
        for p, r in zip(self.publicos, self.rel):
            if p.suffix in {'.js', '.html', '.py', '.md', '.css', '.txt', '.json'}:
                self.assertIsNone(padrao.search(p.read_text(encoding='utf-8', errors='ignore')), r)

    def test_regras_de_classificacao_ficam_fora_do_git(self):
        self.assertNotIn('scripts/regras_classificacao.json', self.rel)
        self.assertIn('scripts/regras_classificacao.json', (RAIZ / '.gitignore').read_text(encoding='utf-8'))

    def test_codigo_publico_nao_tem_listas_de_palavras_chave(self):
        """Palavras-chave vêm de descrições e diagnósticos reais: nenhum .py público pode conter
        listas longas de textos (como o antigo CAT = [...])."""
        import ast
        for p, r in zip(self.publicos, self.rel):
            if p.suffix != '.py' or r.startswith('tests/'):
                continue
            for no in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
                if isinstance(no, (ast.List, ast.Tuple, ast.Set)):
                    textos = [e for e in no.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                    self.assertLess(len(textos), 5, f'{r}:{no.lineno}: lista de palavras no código público')

    def test_palavras_chave_locais_nao_vazam_para_arquivos_publicos(self):
        regras = RAIZ / 'scripts' / 'regras_classificacao.json'
        if not regras.exists():
            self.skipTest('regras locais não estão nesta máquina')
        cfg = json.loads(regras.read_text(encoding='utf-8'))
        chaves = set()
        for grupo in ('uf', 'parceiros', 'tipos', 'saude'):
            for regra in cfg[grupo]:
                for campo in ('contem', 'comeca', 'igual'):
                    chaves |= {norm(k) for k in regra.get(campo, [])}
        # palavras que já são rótulos públicos (categorias, parceiros autorizados, nomes de estados) não contam
        rotulos = norm(' '.join(P.FAIXAS + P.SEXOS + list(P.OUTROS.values())
                                + [r['nome'] for g in ('parceiros', 'tipos', 'saude') for r in cfg[g]]
                                + list(P.ler_autorizados(RAIZ / 'scripts' / 'parceiros_autorizados.txt'))
                                + ['Rio de Janeiro', 'São Paulo', 'Minas Gerais', 'Pernambuco', 'Amapá']))
        exemplo = norm((RAIZ / 'scripts' / 'regras_classificacao.exemplo.json').read_text(encoding='utf-8'))
        # verbos genéricos de atividade aparecem em comentários comuns e não identificam ninguém
        genericas = {'gravar', 'escrever', 'mensag', 'conhecer', 'visita', 'visitar', 'concluir', 'finalizar',
                     'editar', 'contato'}
        distintivas = {k for k in chaves if len(k) >= 5 and k not in rotulos and k not in exemplo and k not in genericas}
        # Onde o vazamento aconteceu: textos literais dos scripts Python e documentos em texto.
        # (js/dados.js é coberto pelo teste de vocabulário; HTML/JS do site não vêm da planilha.)
        import ast
        for p, r in zip(self.publicos, self.rel):
            if p.suffix == '.py' and not r.startswith('tests/'):
                arvore = ast.parse(p.read_text(encoding='utf-8'))
                texto = norm(' '.join(n.value for n in ast.walk(arvore)
                                      if isinstance(n, ast.Constant) and isinstance(n.value, str)))
            elif p.suffix in {'.md', '.txt'}:
                texto = norm(p.read_text(encoding='utf-8', errors='ignore'))
            else:
                continue
            vazadas = [k for k in distintivas if k in texto]
            self.assertEqual(len(vazadas), 0, f'{r}: {len(vazadas)} palavra(s)-chave locais no arquivo público')

    def test_publicacao_automatica_so_envia_o_site(self):
        wf = RAIZ / '.github' / 'workflows' / 'publicar.yml'
        if not wf.exists():
            self.skipTest('sem workflow de publicação')
        t = wf.read_text(encoding='utf-8')
        self.assertIn('python -m unittest discover -s tests', t, 'publicação precisa rodar os testes antes')
        self.assertRegex(t, r'needs:\s*testes', 'deploy precisa depender dos testes')
        self.assertNotRegex(t, r'cp -r[^\n]*(scripts|tests)', 'scripts e testes não podem ir para o site')

    def test_job_de_publicacao_tem_as_permissoes_necessarias(self):
        """As permissões de um job substituem as do workflow; sem contents: read o checkout falha."""
        wf = RAIZ / '.github' / 'workflows' / 'publicar.yml'
        if not wf.exists():
            self.skipTest('sem workflow de publicação')
        job = re.search(r'\n  publicar:\n(.*?)(?=\n  \S|\Z)', wf.read_text(encoding='utf-8'), re.S)
        self.assertIsNotNone(job, 'job "publicar" não encontrado')
        bloco = re.search(r'\n    permissions:\n((?:      .*\n)+)', job.group(1) + '\n')
        self.assertIsNotNone(bloco, 'job "publicar" precisa declarar as próprias permissões')
        perms = dict(re.findall(r'^\s+([\w-]+):\s*(\w+)', bloco.group(1), re.M))
        self.assertEqual(perms, {'contents': 'read', 'pages': 'write', 'id-token': 'write'})


def grupo(total, **kw):
    """Agregado interno FICTÍCIO para testes (contagens simples)."""
    base = dict(total=total, years={2020: total}, cats={'Passeio': total}, ills={'Câncer': total},
                partners={'Hospital A': total}, bands={'19 a 40': total}, sex={'Mulheres': total},
                ageSum=30 * total, ageN=total, impact=10 * total, impactN=total)
    base.update(kw)
    return base


def somar(*gs):
    s = dict(total=0, years=Counter(), cats=Counter(), ills=Counter(), partners=Counter(), bands=Counter(),
             sex=Counter(), ageSum=0, ageN=0, impact=0, impactN=0)
    for g in gs:
        for c in ('total', 'ageSum', 'ageN', 'impact', 'impactN'):
            s[c] += g[c]
        for c in ('years', 'cats', 'ills', 'partners', 'bands', 'sex'):
            s[c].update(g[c])
    return {k: dict(v) if isinstance(v, Counter) else v for k, v in s.items()}


class C_RegrasComCenariosFicticios(unittest.TestCase):
    def test_estado_com_um_registro_nao_vaza_pelo_brasil(self):
        grande = grupo(40, ills={'Câncer': 30, 'Renal': 10})
        pequeno = grupo(1, ills={'Cardíaca': 1}, sex={'Homens': 1}, bands={'71 ou mais': 1})
        saida = P.publicar({'XX': grande, 'YY': pequeno}, somar(grande, pequeno), frozenset({'Hospital A'}), mascarar=False)
        self.assertEqual(saida['YY'], {'total': 1, 'restrito': True})
        # mascarado, um único restrito não pode ser publicado: o total sairia por subtração
        with self.assertRaises(P.ErroPrivacidade):
            P.publicar({'XX': grande, 'YY': pequeno}, somar(grande, pequeno), mascarar=True)
        self.assertNotIn('Cardíaca', dict(saida['BR']['ills']))
        self.assertEqual(saida['BR']['sex'], saida['XX']['sex'])
        self.assertEqual(saida['BR']['bands'], saida['XX']['bands'])
        # um único estado restrito: anos e impacto do Brasil não podem incluí-lo
        self.assertEqual(saida['BR']['years'], saida['XX']['years'])
        self.assertEqual(saida['BR']['impact'], saida['XX']['impact'])
        self.assertEqual(saida['BR']['total'], 41)

    def test_celula_pequena_em_estado_grande_vai_para_outros(self):
        g = grupo(50, ills={'Câncer': 47, 'Transplante': 3}, cats={'Passeio': 49, 'Experiência radical': 1})
        saida = P.publicar({'XX': g}, somar(g))
        self.assertEqual(saida['XX']['ills'], [['Câncer', 47], ['Outras', 3]])
        self.assertEqual(saida['XX']['cats'], [['Passeio', 49], ['Outros tipos', 1]])

    def test_faixa_pequena_omite_distribuicao_e_tira_do_brasil(self):
        a = grupo(30, bands={'Até 18': 28, '71 ou mais': 2})
        b = grupo(20, bands={'19 a 40': 20})
        saida = P.publicar({'XX': a, 'ZZ': b}, somar(a, b))
        self.assertIsNone(saida['XX']['bands'])
        self.assertIsNone(saida['XX']['ageAvg'])
        self.assertEqual(saida['BR']['bands'], saida['ZZ']['bands'])

    def test_parceiro_nao_autorizado_nunca_aparece(self):
        g = grupo(30, partners={'Hospital A': 20, 'Nome Qualquer': 10})
        saida = P.publicar({'XX': g}, somar(g), frozenset({'Hospital A'}))
        nomes = [n for n, _ in saida['XX']['partners']] + [n for n, _ in saida['BR']['partners']]
        self.assertNotIn('Nome Qualquer', nomes)
        self.assertIn('Outras origens', nomes)

    def test_lista_vazia_esconde_todos_os_parceiros(self):
        g = grupo(30)
        saida = P.publicar({'XX': g}, somar(g))
        self.assertEqual(saida['XX']['partners'], [['Outras origens', 30]])

    def test_grupo_de_restritos_grande_mantem_anos_nacionais(self):
        g = grupo(40)
        # anos espalhados: nenhum ano tem mais sonhos do que os outros estados conseguiriam absorver
        r1, r2 = grupo(3, years={2019: 1, 2021: 1, 2022: 1}), grupo(4, years={2019: 2, 2021: 2})
        for mascarar in (False, True):
            saida = P.publicar({'XX': g, 'R1': r1, 'R2': r2}, somar(g, r1, r2), mascarar=mascarar)
            self.assertTrue(saida['BR']['anosIncluemRestritos'])
            self.assertEqual(sum(saida['BR']['years'].values()), 47)
            self.assertEqual(P.validar(saida), [])
            for u in ('R1', 'R2'):
                self.assertEqual(set(saida[u]), P.CAMPOS_RESTRITO_MASCARADO if mascarar else P.CAMPOS_RESTRITO)

    def test_ano_atribuivel_tira_restritos_dos_anos_do_brasil(self):
        """Restrito com 6 de 8 sonhos e um ano com 4: o estado teria >= 2 naquele ano (Fréchet)."""
        g = grupo(40)
        r1 = grupo(6, years={2022: 4, 2021: 2})
        r2, r3 = grupo(1, years={2023: 1}), grupo(1, years={2024: 1})
        saida = P.publicar({'XX': g, 'R1': r1, 'R2': r2, 'R3': r3}, somar(g, r1, r2, r3), mascarar=False)
        self.assertFalse(saida['BR']['anosIncluemRestritos'])
        self.assertEqual(saida['BR']['years'], saida['XX']['years'])
        self.assertEqual(P.validar(saida), [])
        # com totais mascarados, nenhum ano é atribuível e o gráfico nacional fica completo
        m = P.publicar({'XX': g, 'R1': r1, 'R2': r2, 'R3': r3}, somar(g, r1, r2, r3), mascarar=True)
        self.assertTrue(m['BR']['anosIncluemRestritos'])
        self.assertEqual(m['R1'], {'restrito': True, 'totalMax': P.LIMITE_DETALHE - 1})
        self.assertEqual(P.validar(m), [])

    def test_mascarar_recusa_soma_que_revela_os_totais(self):
        g = grupo(40)
        r1, r2 = grupo(1, years={2019: 1}), grupo(1, years={2021: 1})  # 2 estados somando 2 => cada um tem 1
        with self.assertRaises(P.ErroPrivacidade):
            P.publicar({'XX': g, 'R1': r1, 'R2': r2}, somar(g, r1, r2), mascarar=True)
        with self.assertRaises(P.ErroPrivacidade):  # um único estado restrito: a soma é o próprio total
            P.publicar({'XX': g, 'R1': grupo(4)}, somar(g, grupo(4)), mascarar=True)

    def test_validador_pega_arquivo_adulterado(self):
        g, r1, r2 = grupo(40, ills={'Câncer': 30, 'Renal': 10}), grupo(3), grupo(4)
        saida = P.publicar({'XX': g, 'R1': r1, 'R2': r2}, somar(g, r1, r2), mascarar=False)
        self.assertEqual(P.validar(saida), [])
        ruim = json.loads(json.dumps(saida))
        ruim['BR']['ills'].append(['Cardíaca', 1])  # célula pequena + diferença Brasil − estados
        ruim['R1']['ills'] = [['Câncer', 3]]          # detalhe em estado restrito
        erros = P.validar(ruim)
        self.assertTrue(any('restrito' in e for e in erros))
        self.assertTrue(any('ills' in e for e in erros))
        self.assertTrue(all('Cardíaca' not in e and ' 1' not in e for e in erros), 'mensagem revela valores')

    def test_atualizacao_pequena_entre_versoes_e_bloqueada(self):
        a, b = grupo(40), grupo(42)
        antes, depois = P.publicar({'XX': a}, somar(a)), P.publicar({'XX': b}, somar(b))
        self.assertTrue(P.validar_atualizacao(antes, depois))
        self.assertEqual(P.validar_atualizacao(antes, P.publicar({'XX': grupo(46)}, somar(grupo(46)))), [])
        self.assertEqual(P.validar_atualizacao(None, depois), [])

    def test_sonhos_sem_estado_contam_no_brasil_e_nao_ajudam_a_deduzir(self):
        g = grupo(40)
        r1, r2 = grupo(3, years={2019: 1, 2021: 1, 2022: 1}), grupo(4, years={2019: 2, 2021: 2})
        sem = grupo(2, years={2023: 2})  # registros sem estado identificado
        for mascarar in (False, True):
            saida = P.publicar({'XX': g, 'R1': r1, 'R2': r2}, somar(g, r1, r2, sem), mascarar=mascarar, sem_uf=2)
            self.assertEqual(saida['BR']['total'], 49)
            self.assertEqual(saida['BR']['semUF'], 2)
            self.assertNotIn(None, saida)
            self.assertEqual(P.validar(saida), [])

    def test_somas_inconsistentes_sao_recusadas(self):
        g = grupo(40)
        with self.assertRaises(P.ErroPrivacidade):  # Brasil com 2 registros que não estão em estado nem em sem_uf
            P.publicar({'XX': g}, somar(g, grupo(2)), mascarar=False)

    def test_media_de_idade_do_brasil_usa_somas_exatas(self):
        a = grupo(20, ageSum=400, ageN=20)  # média 20
        b = grupo(10, ageSum=600, ageN=10, bands={'41 a 70': 10})  # média 60
        saida = P.publicar({'XX': a, 'ZZ': b}, somar(a, b))
        self.assertEqual(saida['BR']['ageAvg'], round(1000 / 30))


class E_GeracaoCompletaComPlanilhaFicticia(unittest.TestCase):
    """Roda preparar_dados.py de ponta a ponta numa planilha FICTÍCIA criada aqui (num diretório
    temporário), com as regras do modelo público: o que sair precisa passar no validador."""

    @classmethod
    def setUpClass(cls):
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            raise unittest.SkipTest('openpyxl não instalado')
        import importlib.util, tempfile
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        spec = importlib.util.spec_from_file_location('preparar_dados_teste', RAIZ / 'scripts' / 'preparar_dados.py')
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        (cls.tmp / 'pessoas.txt').write_text('Fulana Ficticia\n', encoding='utf-8')
        # modelo público + uma UF extra (fictícia para o teste) para haver 2 estados restritos
        regras = json.loads((RAIZ / 'scripts' / 'regras_classificacao.exemplo.json').read_text(encoding='utf-8'))
        regras['uf'].append({'uf': 'PE', 'contem': ['cidade teste pe']})
        regras['uf_padrao'] = None
        (cls.tmp / 'regras.json').write_text(json.dumps(regras, ensure_ascii=False), encoding='utf-8')
        cls.mod.carregar_regras(cls.tmp / 'regras.json', cls.tmp / 'pessoas.txt')

    def planilha(self, linhas):
        import datetime, openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'sonhos'
        for _ in range(5):
            ws.append([None])
        for i, (sexo, idade, origem, ano, sonho, saude, imp) in enumerate(linhas, 1):
            ws.append([i, 'Pessoa Ficticia', sexo, None, idade, origem, datetime.datetime(ano, 5, 1), sonho, saude,
                       None, None, imp])
        caminho = self.tmp / f'p{len(linhas)}.xlsx'
        wb.save(caminho)
        return caminho

    def test_pipeline_aplica_e_valida_as_regras(self):
        linhas = [('M', 30 + i % 40, 'INCA', 2020 + i % 4, 'passeio na praia', 'cancer', 10) for i in range(30)]
        linhas += [('H', 8, 'Fulana Ficticia', 2021, 'mensagem de video', 'avc', 5)]      # pessoa física
        linhas += [('H', 70, 'Clinica Inventada', 2022, 'algo raro', 'doenca rara', 3)]  # parceiro não autorizado
        linhas += [('M', 50, 'sao paulo', 2023, 'passeio', 'cancer', 2)] * 2               # SP com 2 => restrito
        linhas += [('H', 60, 'cidade teste pe', 2022, 'passeio', 'cancer', 2)] * 3          # PE com 3 => restrito
        saida_js = self.tmp / 'dados.js'
        saida = self.mod.gerar(self.planilha(linhas), saida_js, autorizados=frozenset({'INCA'}))
        texto = saida_js.read_text(encoding='utf-8')
        self.assertEqual(P.validar(saida, frozenset({'INCA'})), [])
        restrito = {'restrito': True, 'totalMax': 9} if P.MASCARAR_RESTRITOS else {'total': 2, 'restrito': True}
        self.assertEqual(saida['SP'], restrito)
        # origem desconhecida: conta no Brasil, sem virar RJ
        self.assertEqual(saida['BR']['semUF'], 1)
        self.assertEqual(saida['RJ']['total'], 31)
        self.assertEqual(saida['BR']['total'], 31 + 1 + 2 + 3)
        for proibido in ('Fulana', 'Ficticia', 'Clinica Inventada', 'algo raro', 'doenca rara', 'Pessoa'):
            self.assertNotIn(proibido, texto)
        self.assertFalse(list(self.tmp.glob('*.tmp')), 'arquivo temporário ficou para trás')

    def test_sexo_nao_informado_e_anos_novos(self):
        linhas = [('M', 30, 'INCA', 2025, 'passeio', 'cancer', 1)] * 12
        linhas += [('H', 40, 'INCA', 2026, 'passeio', 'cancer', 1)] * 6
        linhas += [('', 50, 'INCA', 2027, 'passeio', 'cancer', 1)] * 6      # sexo vazio e um ano novo
        linhas += [('X', 60, 'INCA', 2028, 'passeio', 'cancer', 1)]          # sexo desconhecido
        linhas += [('M', 50, 'sao paulo', 2027, 'passeio', 'cancer', 1)] * 2
        linhas += [('H', 50, 'cidade teste pe', 2028, 'passeio', 'cancer', 1)] * 3
        saida = self.mod.gerar(self.planilha(linhas), self.tmp / 'dados_sexo.js', autorizados=frozenset({'INCA'}),
                               forcar_atualizacao=True)
        rj = saida['RJ']
        self.assertEqual(rj['total'], 25)
        self.assertEqual(rj['sex'], {'Mulheres': 12, 'Homens': 6}, 'vazio e "X" não podem virar "Mulheres"')
        self.assertEqual(rj['last'], 2028)
        self.assertIn('2027', saida['BR']['years'])
        self.assertEqual(saida['BR']['last'], 2028)
        self.assertEqual(P.validar(saida, frozenset({'INCA'})), [])

    def test_relatorio_de_revisao_local(self):
        linhas = [('M', 30, 'INCA', 2025, 'passeio', 'cancer', 1)] * 20
        linhas += [('', 40, 'Origem Inventada', 2025, 'um sentimento bom', 'doenca x', 1)]
        linhas += [('M', 50, 'sao paulo', 2025, 'passeio', 'cancer', 1)] * 2
        linhas += [('H', 50, 'cidade teste pe', 2025, 'passeio', 'cancer', 1)] * 3
        rel = self.tmp / 'revisao_classificacao.csv'
        js = self.tmp / 'dados_revisao.js'
        self.mod.gerar(self.planilha(linhas), js, autorizados=frozenset({'INCA'}), forcar_atualizacao=True, revisao=rel)
        texto = rel.read_text(encoding='utf-8-sig')
        for motivo in ('valor não reconhecido', 'origem fora das listas', 'nome bruto', 'categoria padrão'):
            self.assertIn(motivo, texto)
        self.assertIn('*.csv', (RAIZ / '.gitignore').read_text(encoding='utf-8'))
        self.assertNotIn('Origem Inventada', js.read_text(encoding='utf-8'))

    def test_pipeline_mascarado_recusa_um_unico_estado_restrito(self):
        if not P.MASCARAR_RESTRITOS:
            self.skipTest('totais exatos')
        linhas = [('M', 40, 'INCA', 2021, 'passeio', 'cancer', 1)] * 20 + [('M', 50, 'sao paulo', 2023, 'passeio', 'cancer', 2)]
        destino = self.tmp / 'dados_unico.js'
        with self.assertRaises(SystemExit):
            self.mod.gerar(self.planilha(linhas), destino, autorizados=frozenset({'INCA'}))
        self.assertFalse(destino.exists(), 'nada pode ser gravado quando a publicação é recusada')

    def test_pipeline_recusa_atualizacao_pequena(self):
        base = [('M', 40, 'INCA', 2021, 'passeio', 'cancer', 1)] * 20
        destino = self.tmp / 'dados_atualizacao.js'
        self.mod.gerar(self.planilha(base), destino, autorizados=frozenset({'INCA'}))
        antes = destino.read_text(encoding='utf-8')
        with self.assertRaises(SystemExit):
            self.mod.gerar(self.planilha(base + base[:2]), destino, autorizados=frozenset({'INCA'}))
        self.assertEqual(destino.read_text(encoding='utf-8'), antes, 'arquivo foi alterado mesmo recusado')


class D_Interface(unittest.TestCase):
    def test_botao_voltar_respeita_hidden(self):
        css = (RAIZ / 'css' / 'estilo.css').read_text(encoding='utf-8')
        self.assertRegex(css, r'\.botao-voltar\[hidden\]\s*\{\s*display\s*:\s*none')

    def test_esc_fecha_tooltip(self):
        js = (RAIZ / 'js' / 'app.js').read_text(encoding='utf-8')
        self.assertRegex(js, r"key === 'Escape'\)\s*\{\s*R\.esconderTooltip\(\)")


if __name__ == '__main__':
    unittest.main()
