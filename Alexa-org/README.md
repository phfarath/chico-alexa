# C.H.I.C.O. — Assistente Virtual 🤖

> CP4 — Projeto 2º Semestre | FIAP — Engenharia de Software

Assistente virtual por reconhecimento de voz.
Só executa ações após reconhecer o nome **"Chico"** — assim como uma assistente real.

---

## 📋 Funcionalidades

| # | Comando | Descrição |
|---|---------|-----------|
| 1 | `Chico` | Ativa a assistente para receber comandos |
| 2 | `Chico cadastrar evento na agenda` | Salva um evento em `agenda.txt` |
| 3 | `Chico ler agenda` | Lê todos os eventos cadastrados |
| 4 | `Chico que horas são?` | Informa a hora atual |
| 5 | `Chico que dia é hoje?` | Informa o dia da semana e data |
| 6 | `Chico calcular 10 mais 5` | Operações básicas (+, -, ×, ÷) |
| 7a | `Chico cadastrar rosto` | Tira fotos e treina o modelo com o seu nome |
| 7b | `Chico reconhecer face` / `quem sou eu?` | Abre a webcam e identifica a pessoa |
| 8 | `Chico limpar agenda` | Apaga todos os eventos da agenda |
| 9 | `Chico o que é machine learning?` | Consulta o Google Gemini (IA generativa) |
| 10a | `Chico previsão do tempo em São Paulo` | Clima em tempo real (Open-Meteo) |
| 10b | `Chico qual o valor do dólar` | Cotação USD-BRL em tempo real |
| 10c | `Chico quanto vale um bitcoin` | Cotação BTC-BRL em tempo real |
| 10d | `Chico tocar Shape of You no Spotify` | Toca a faixa no app do Spotify |
| 10d+ | `Chico pausar` / `próxima` / `anterior` / `continuar` | Controla a reprodução |
| 10e | `Chico pesquisar Python no Google` | Abre busca no Google |
| 10f | `Chico aumenta o volume` / `diminui` / `mutar` | Controle de volume (Windows pycaw / Mac osascript) |
| 10g | `Chico tira um print da tela` | Screenshot cross-platform (mss) |
| 10h | `Chico abre o YouTube e toca um vídeo sobre Python` | Abre YouTube pesquisando o tema |
| 10i | `Chico abre o portal da faculdade` | Abre o portal FIAP |
| 11a | `Chico modo foco` | Rotina: muta volume, pausa Spotify e registra na agenda |
| 11b | `Chico modo aula sobre Python` | Rotina: portal FIAP + YouTube no tema + registro na agenda |
| 11c | `Chico bom dia` | Briefing falado: data, hora, agenda, clima e dólar |
| 12a | `Chico o que tem na minha tela?` | Print + Gemini descreve o que está no monitor |
| 12b | `Chico descreve a cena` | Foto da webcam + Gemini descreve o ambiente |
| 13a | `Chico abre meu trabalho` | Busca fuzzy em Documents/Desktop/Downloads e abre o arquivo |
| 13b | `Chico bloqueia a tela` | Trava a sessão (Windows/Mac/Linux) |
| 13c | `Chico agenda desligamento em 30 minutos` | Agenda o desligamento (`cancela o desligamento` desfaz) |
| 13d | `Chico o que tem no clipboard?` | Lê a área de transferência e resume com a IA |
| 14a | `Chico anota uma ideia: ...` | Ditado vira nota estruturada em `data/notas.md` |
| 14b | `Chico o que eu anotei?` | Lê as notas (IA resume quando está longo) |
| 14c | `Chico lê o pdf do trabalho` | Localiza o PDF pelo nome, extrai e resume com a IA |
| 15a | `Chico me lembra da prova às 8 e vê o clima` | **Planner por function calling**: a IA encadeia várias ações de uma frase |
| 15b | `Chico para de me interromper` / `liga o modo proativo` | Liga/desliga os avisos espontâneos (lembretes + presença) |
| 15c | `Chico esquece tudo que eu falei` | Zera a memória de conversa da IA |

> Itens 10f–10i são extras do item 10 do PDF (cross-platform Windows/Mac com retry automático).
> Itens 11–14 são o **Tier 1**: funcionalidades que fazem o Chico enxergar, encadear ações e mexer no PC — cada uma segue a mesma receita do projeto (módulo + frases-exemplo no roteador + handler).
> Item 15 é o **Tier 2**: o Chico vira agente — planeja chamadas de função, fala primeiro e lembra da conversa.

> **Regra obrigatória:** qualquer comando só é processado após o usuário dizer "Chico".

---

## 🗂️ Estrutura do Projeto

```
.
├── main.py                  # Ponto de entrada
├── chico.py                 # Classe principal Chico (orquestra tudo)
├── agenda.py                # Cadastrar, ler e limpar agenda
├── calculadora.py           # Cálculo com expressões em português
├── sistema.py               # Hora e data
├── ia_generativa.py         # Integração com Google Gemini (texto + imagem)
├── clima.py                 # Previsão do tempo (Open-Meteo)
├── financas.py              # Dólar (AwesomeAPI) e Bitcoin (CoinGecko)
├── midia.py                 # Spotify e Google
├── face.py                  # Reconhecimento facial (OpenCV)
├── tts.py                   # Voz neural (edge-tts) + fallback pyttsx3
├── roteador.py              # Roteamento por embeddings (TF-IDF + Gemini opcional)
├── extras.py                # Comandos extras cross-platform (volume, screenshot, YouTube)
├── rotinas.py               # Tier 1: rotinas/modos (foco, aula, bom dia)
├── visao.py                 # Tier 1: descreve a tela e a câmera via Gemini
├── desktop.py               # Tier 1: abrir arquivo, bloquear tela, desligamento, clipboard
├── notas.py                 # Tier 1: anotações faladas e leitura de PDF
├── agente.py                # Tier 2: planner por function calling do Gemini
├── proativo.py              # Tier 2: lembretes da agenda + detecção de presença
├── data/
│   ├── agenda.txt           # Eventos da agenda (gerado automaticamente)
│   ├── notas.md             # Caderno de notas (gerado automaticamente)
│   ├── screenshots/         # Prints da tela (gerado automaticamente)
│   ├── face_model.yml       # Modelo LBPH treinado (gerado via face.py)
│   ├── face_nomes.txt       # Nomes do modelo
│   └── rostos/<nome>/*.jpg  # Fotos para treino (60 por pessoa)
├── requirements.txt
├── .env.example             # Modelo de variáveis de ambiente
└── README.md
```

---

## ⚙️ Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/chico-assistente.git
cd chico-assistente
```

### 2. Crie e ative um ambiente virtual (Python 3.11)
```bash
py -3.11 -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

> **Windows — PyAudio:**
> Se der erro ao instalar o PyAudio:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 4. Configure a chave do Gemini

1. Acesse [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Crie uma chave gratuita
3. Copie `.env.example` para `.env` e insira a chave:
```env
GEMINI_API_KEY=sua_chave_aqui
```

### 5. Configure o Spotify (playback de verdade)

A API do Spotify **não entrega o áudio** para o Python. O Chico busca a faixa e manda o **app desktop do Spotify** tocar.

1. Instale o [Spotify](https://www.spotify.com/download/) no computador e faça login (conta **Premium** reproduz qualquer faixa; Free tem as limitações do próprio Spotify).
2. Crie um app em [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).
3. Copie Client ID e Client Secret para o `.env`:
```env
SPOTIFY_CLIENT_ID=seu_client_id
SPOTIFY_CLIENT_SECRET=seu_client_secret
```

Sem essas chaves, o Chico só abre a busca no navegador (comportamento antigo).

### 6. Execute
```bash
python main.py
```

---

## 🎤 Como usar

Ao iniciar, o sistema aguarda você dizer (ou digitar) **"Chico"** seguido do comando:

```
⌨️  Digite o comando (Enter para usar voz): chico que horas são
🤖 Chico: São 14 horas e 30 minutos.
```

Ou apenas pressione Enter para usar o microfone:
```
🎙️  Aguardando ativação ('Chico')...
   ✅ Reconhecido: 'chico cadastrar evento na agenda'
🤖 Chico: Ok! Qual evento devo cadastrar?
```

---

## 🧠 Reconhecimento Facial

O modelo **não vem pronto**: primeiro cadastre o rosto, depois reconheça.

1. `Chico cadastrar rosto` → diga o nome → olhe para a câmera (60 fotos) → o modelo é treinado sozinho
2. `Chico quem sou eu?` ou `Chico reconhecer face` → a câmera identifica a pessoa
3. Na janela da câmera, pressione **q** para encerrar (ou aguarde: fecha sozinha ao confirmar a pessoa)

No macOS, autorize o Terminal/Cursor em **Ajustes → Privacidade e Segurança → Câmera**.

**Melhorias no reconhecimento facial:**
- Alinhamento do rosto pelos olhos + normalização de contraste (CLAHE), tornando o modelo mais tolerante a inclinação de cabeça e luz irregular.
- Filtros de qualidade na captura: só salva fotos nítidas, bem iluminadas e com o rosto perto o bastante da câmera — mostra na tela o que ajustar.
- Dicas de pose durante o cadastro (virar levemente a cabeça, sorrir) para variar o ângulo capturado.
- Recadastrar uma pessoa **adiciona** fotos novas em vez de sobrescrever as antigas.
- Treino com pequenas variações (rotação leve e brilho) de cada foto, para generalizar melhor com poucas fotos.
- Reconhecimento por votação em vários frames (não decide só pelo último frame antes de fechar a câmera) e fecha sozinho ao confirmar a pessoa.
- Correção do nome: frases como "meu nome é Pedro" agora viram a pasta `pedro`, não `meu_nome_e_pedro`.

> Se você já tinha rostos cadastrados antes dessas melhorias, vale apagar `data/rostos/`, `data/face_model.yml` e `data/face_nomes.txt` e cadastrar de novo — assim todas as fotos já ficam alinhadas e normalizadas do mesmo jeito.

Também dá para treinar sem a assistente:

```bash
python face.py cadastrar Maria
python face.py reconhecer
```

---

## 🧭 Roteamento por Embeddings

Comandos **não são** `if "palavra" in frase`. O `roteador.py` vetoriza a frase e compara (cosseno) com exemplos de cada intent.

- **Padrão:** TF-IDF offline (sklearn, instantâneo, sem internet) — já vem pronto.
- **Opcional:** embeddings reais do Gemini (`text-embedding-004`) — descomente o bloco em `roteador.py:_vetorizar` e use `Roteador(usar_gemini=True)` (precisa de `GEMINI_API_KEY`).

```bash
# Testa o roteador sem microfone
.venv\Scripts\python.exe roteador.py
# ou uma frase especifica
.venv\Scripts\python.exe -c "from roteador import Roteador; print(Roteador().explicar('aumenta o volume'))"
```

Isso pega variações tipo "marca um compromisso pra mim" → `cadastrar_agenda` ou "me diz o horário atual" → `hora` sem cadastrar cada sinônimo.

---

## 🧩 Tier 1 — O Chico enxerga, encadeia e mexe no PC

Novos módulos que **orquestram os que já existiam** (injeção de dependência: recebem
as instâncias no `__init__`, nada foi reescrito):

- **`rotinas.py`** — uma frase, várias ações. `modo foco` = muta volume + pausa Spotify +
  registro na agenda; `modo aula sobre X` = portal FIAP + YouTube no tema + registro;
  `bom dia` = briefing falado com data, hora, agenda, clima e dólar.
- **`visao.py`** — os olhos do Chico. `o que tem na minha tela?` reusa `extras.capturar_tela()`
  e manda o PNG ao Gemini multimodal; `descreve a cena` tira foto pela webcam (cv2) e descreve.
- **`desktop.py`** — ações no PC. `abre meu trabalho` faz busca fuzzy por nome em
  Documents/Desktop/Downloads (difflib, score mínimo 0.35); `bloqueia a tela` usa o comando
  nativo de cada SO; `agenda desligamento em N minutos` (Windows `shutdown /s`, Mac/Linux
  orienta o `sudo`); `o que tem no clipboard?` lê pyperclip/nativo e a IA resume.
- **`notas.py`** — caderno falado em `data/notas.md`. `anota uma ideia: ...` a IA titula e
  estrutura (sem IA, salva o texto cru); `o que eu anotei?` resume; `lê o pdf X` acha o PDF
  pelo nome, extrai com pypdf e resume.

```bash
# Testa cada módulo isolado (com fakes, sem microfone/Gemini)
python rotinas.py
python visao.py
python desktop.py
python notas.py
```

---

## 🤖 Tier 2 — O Chico vira agente

O salto de "uma frase → uma ação" para **planejamento**: três peças novas, mesma
receita (módulo + intent + handler).

- **`agente.py`** — planner por *function calling*. Quando o roteador não
  reconhece o intent (ou a frase pede várias coisas), o Gemini recebe ~20
  ferramentas que apontam 1:1 para métodos já existentes (`agenda.cadastrar_evento`,
  `clima.buscar_previsao`, `desktop.abrir_arquivo`...) e devolve chamadas de
  função encadeadas. Cada resultado é falado na hora e volta ao modelo até ele
  concluir. Ex.: `Chico me lembra da prova às 8 e vê o clima` → agenda + clima.
  Sem `GEMINI_API_KEY`, o planner nem é consultado e o fallback antigo responde.
- **`proativo.py`** — o Chico fala primeiro. Thread daemon checa a agenda a cada
  30s: eventos com horário no texto ("prova às 18h") disparam lembrete na hora.
  A cada 5min, um frame da webcam passa pelo Haar (mesmo detector do `face.py`):
  na transição ausente→presente ele saúda, com cooldown de 45min. Sem câmera,
  falha em silêncio. `para de me interromper` desliga sem matar a thread.
- **memória** — `ia_generativa` guarda as últimas 10 trocas e injeta no contexto:
  follow-ups tipo `e por quê?` funcionam. `esquece tudo que eu falei` zera.

```bash
python agente.py    # valida o mapa de tools (sem API)
python proativo.py  # parse de horário + janela de lembrete (sem câmera)
```

---

## 📦 Dependências Principais

| Biblioteca | Versão | Uso |
|-----------|--------|-----|
| SpeechRecognition | 3.10.4 | Reconhecimento de voz (Google STT) |
| pyttsx3 | 2.99 | Síntese de voz offline (fallback) |
| edge-tts | 7.2.3 | Voz neural pt-BR |
| pygame | 2.6.1 | Reprodução de áudio no Windows (sem abrir player) |
| PyAudio | 0.2.14 | Captura de áudio do microfone |
| google-genai | 1.2.0 | Google Gemini (IA generativa) |
| scikit-learn | 1.5.2 | Roteamento por embeddings (TF-IDF) |
| opencv-python | 4.10.0.84 | Reconhecimento facial (Haar) |
| opencv-contrib-python | 4.10.0.84 | LBPHFaceRecognizer |
| mss | 10.2.0 | Screenshot cross-platform |
| pycaw | 20251023 | Controle de volume no Windows |
| requests | 2.32.3 | APIs de clima e cotações |
| pypdf | 5.4.0 | Extração de texto de PDF (notas.py) |
| pyperclip | 1.9.0 | Área de transferência (desktop.py) |
| python-dotenv | 1.0.1 | Variáveis de ambiente |

---

## 👥 Grupo

| Nome | RM |
|------|----|
| Pedro Farath | 565007 |
| [Nome 2] | [RM] |
| [Nome 3] | [RM] |
| [Nome 4] | [RM] |
| [Nome 5] | [RM] |
| [Nome 6] | [RM] |
| [Nome 7] | [RM] |

> TODO: preencher os 6 nomes/RMs restantes antes de enviar o link no Forms.

---

## 📄 Licença

Projeto acadêmico — FIAP 2026.
