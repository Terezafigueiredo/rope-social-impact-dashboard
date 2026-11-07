# Mapa dos Sonhos Realizados · Instituto ROPE

Dashboard interativo e público que mostra, no mapa do Brasil, o impacto do **[Instituto ROPE](https://www.institutorope.com.br/)**, organização que realiza sonhos de pessoas em fase terminal.

**[▶ Ver o dashboard ao vivo](https://terezafigueiredo.github.io/rope-social-impact-dashboard/)**

## Funcionalidades

- **Indicadores de impacto:** sonhos realizados, estados atendidos, pessoas impactadas e período registrado, com contagem animada.
- **Mapa interativo do Brasil:**
  - estados coloridos pela quantidade de sonhos (escala logarítmica)
  - marcadores dourados pulsantes e tooltip
  - zoom animado ao selecionar um estado
- **Painel de detalhamento:** os cartões "saem" do estado clicado (técnica FLIP com a Web Animations API) e mostram:
  - sonhos e pessoas impactadas
  - tipos de sonho
  - faixa etária
  - instituições parceiras
  - mulheres e homens
  - grupos de condições de saúde
- **Sonhos por ano:** gráfico de colunas do Brasil ou do estado selecionado.
- **Mapa sem dependências externas:** os contornos dos estados vêm da malha territorial do IBGE e ficam no próprio site (`js/mapa-ufs.js`). Se esse arquivo faltar, a página troca para um mapa em grade dos 27 estados e continua funcionando.
- **Responsivo:** o layout se reorganiza de verdade, testado em 320, 375, 390, 768, 1024 e 1440 px.

## Acessibilidade

- HTML semântico, link "Pular para o mapa" e foco visível.
- **Teclado:** Tab chega aos estados e Enter abre o detalhe. Esc volta ao Brasil e o foco é devolvido.
- **Seletor de estados em botões**, uma alternativa ao mapa para teclado, leitores de tela e toque.
- Gráficos com descrição em texto (tabelas e rótulos para leitores de tela), valores e percentuais escritos, sem depender só da cor.
- Respeita `prefers-reduced-motion` e tem um botão **Pausar animações**.

## Privacidade

A base original contém dados sensíveis de pacientes. O dashboard publica **apenas números agregados**:

- Nenhum nome, contato, data individual ou descrição de sonho é publicado.
- **Estados com menos de 10 sonhos mostram só "menos de 10".** Nem o número exato nem qualquer outro dado desses estados vai para o arquivo público, nem escondido.
- **Grupos com menos de 5 pessoas** (um tipo de sonho, uma condição de saúde, uma instituição) são somados em "outros". Faixa etária e sexo são omitidos inteiros quando alguma faixa ficaria abaixo desse limite.
- **Sem dedução por subtração:** os detalhes do Brasil são a soma exata do que é publicado para os estados detalhados. Brasil menos estados dá zero em qualquer categoria.
- **Sem dedução de anos:** o gráfico nacional por ano só inclui os estados com poucos registros se nenhum ano puder ser atribuído a um deles (verificação pelos limites de Fréchet).
- **Totais mascarados** (`MASCARAR_RESTRITOS = True` em `scripts/privacidade.py`): o mapa usa a mesma cor e os botões seguem ordem alfabética para esses estados, para que nada revele quem tem mais. O script recusa a publicação se a soma do Brasil permitir deduzir algum total.
- **Atualizações:** o script recusa uma nova versão em que algum estado tenha ganhado de 1 a 4 sonhos, porque comparar as duas versões revelaria os casos novos.
- **Instituições** só aparecem pelo nome se estiverem em `scripts/parceiros_autorizados.txt`. As demais são somadas em "Outras origens". **Indicações feitas por pessoas físicas** aparecem como "Indicação individual", e a lista desses nomes fica num arquivo local fora do Git.
- A planilha original **não** faz parte do repositório (veja o `.gitignore`).
- As regras ficam em `scripts/privacidade.py` e são verificadas por testes automáticos (veja abaixo).

## Estrutura

```
index.html            estrutura semântica da página
css/estilo.css        identidade visual, responsividade e movimento reduzido
js/dados.js           dados agregados (gerado pelo script Python)
js/mapa-ufs.js        contornos das UFs (gerado da malha do IBGE)
js/utils.js           formatação, tooltip, contagem e preferência de movimento
js/efeitos.js         céu com estrelas e partículas (canvas, ~30 fps, pausa quando oculto)
js/graficos.js        colunas, barras, rosca e descrições acessíveis
js/mapa.js            contornos, marcadores, zoom e plano B em grade
js/painel.js          cartões do painel e animações de entrada e saída
js/app.js             orquestra indicadores, seletor e navegação
assets/logo-rope.png  logo oficial do Instituto ROPE
assets/fontes/        Fraunces e Nunito Sans hospedadas no site (licença SIL OFL 1.1)
scripts/preparar_dados.py   limpeza e agregação da planilha
scripts/privacidade.py      regras de privacidade aplicadas antes de publicar
scripts/parceiros_autorizados.txt   instituições que podem aparecer pelo nome
scripts/preparar_mapa.py    conversão da malha do IBGE
tests/test_privacidade.py   testes de privacidade e segurança
```

## Dados: da planilha ao painel

```bash
pip install openpyxl
cp scripts/regras_classificacao.exemplo.json scripts/regras_classificacao.json   # preencher localmente
python scripts/preparar_dados.py planilha.xlsx js/dados.js
```

As palavras-chave de classificação ficam em `scripts/regras_classificacao.json`, **fora do Git**, porque são derivadas das descrições e dos diagnósticos reais. O script só grava o `js/dados.js` se o validador de privacidade não encontrar nenhum problema.

O script:
- descarta as linhas que separam os anos e corrige datas digitadas como texto;
- atribui o estado de cada sonho pela instituição que o indicou;
- padroniza os nomes das instituições;
- classifica tipos de sonho e condições de saúde por palavras-chave;
- agrega tudo por estado, aplicando as regras de privacidade.

Antes de publicar, rode os testes (só a biblioteca padrão do Python):

```bash
python -m unittest discover -s tests -v
```

Eles verificam que nenhum dado restrito pode ser recuperado por subtração, por inspeção do `js/dados.js` ou pelos arquivos do repositório, e que o site não carrega nenhum recurso de terceiros (scripts, estilos ou fontes).

### Testes que dependem de arquivos locais

Dois testes usam arquivos confidenciais que ficam fora do Git. Quando o arquivo não está na máquina, o teste aparece como **pulado** (`skipped`), e não como aprovado:

| Teste | Arquivo local | O que verifica |
|---|---|---|
| `test_palavras_chave_locais_nao_vazam_para_arquivos_publicos` | `scripts/regras_classificacao.json` | Nenhuma palavra-chave real aparece em arquivos públicos |
| `test_nomes_de_pessoas_fisicas_nao_aparecem` | `scripts/indicacoes_individuais.txt` | Nenhum nome de quem indicou um sonho aparece em arquivos públicos |

Registro da validação de 07/11/2026, antes da publicação:

- **Palavras-chave locais:** executado com o arquivo real e aprovado. A mesma verificação também cobriu todo o histórico de commits.
- **Nomes de pessoas físicas:** **não executado**, porque o arquivo original não estava disponível. Nenhum arquivo fictício foi usado no lugar dele. Proteções que continuam valendo: o `js/dados.js` só pode conter os parceiros de `scripts/parceiros_autorizados.txt` e os rótulos "Indicação individual" e "Outras origens", e o teste de vocabulário reprova qualquer outro texto.

A publicação no GitHub Pages é feita por `.github/workflows/publicar.yml`: os testes rodam primeiro, e só os arquivos do site (`index.html`, `css/`, `js/`, `assets/`) vão para o ar.

## Rodando localmente

Não precisa de servidor nem de instalação: basta abrir o `index.html` no navegador. Os dados estão em `.js`, e não em `.json`, justamente para funcionar abrindo o arquivo direto.

## Tecnologias

HTML, CSS e JavaScript puros (sem frameworks) · SVG · Canvas · Web Animations API · Python + openpyxl · GitHub Pages

## Autora

**Tereza Figueiredo**, estudante de Análise e Desenvolvimento de Sistemas (Estácio). Tenho interesse em dados, automação e desenvolvimento full stack.
[github.com/Terezafigueiredo](https://github.com/Terezafigueiredo)

---
Contornos dos estados: [Malha territorial do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas) (API de Malhas, qualidade mínima, 27 UFs). Logo: Instituto ROPE. Fontes: [Fraunces](https://github.com/undercasetype/Fraunces) e [Nunito Sans](https://github.com/Fonthausen/NunitoSans), sob a SIL Open Font License 1.1.
