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
├── ia_generativa.py         # Integração com Google Gemini
├── clima.py                 # Previsão do tempo (Open-Meteo)
├── financas.py              # Dólar (AwesomeAPI) e Bitcoin (CoinGecko)
├── midia.py                 # Spotify e Google
├── face.py                  # Reconhecimento facial (OpenCV)
├── tts.py                   # Voz neural (edge-tts) + fallback pyttsx3
├── data/
│   ├── agenda.txt           # Eventos da agenda (gerado automaticamente)
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

## 📦 Dependências Principais

| Biblioteca | Versão | Uso |
|-----------|--------|-----|
| SpeechRecognition | 3.10.4 | Reconhecimento de voz (Google STT) |
| pyttsx3 | 2.99 | Síntese de voz offline (fallback) |
| edge-tts | 7.2.3 | Voz neural pt-BR |
| pygame | 2.6.1 | Reprodução de áudio no Windows (sem abrir player) |
| PyAudio | 0.2.14 | Captura de áudio do microfone |
| google-genai | 1.2.0 | Google Gemini (IA generativa) |
| opencv-python | 4.10.0.84 | Reconhecimento facial (Haar) |
| opencv-contrib-python | 4.10.0.84 | LBPHFaceRecognizer |
| requests | 2.32.3 | APIs de clima e cotações |
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
