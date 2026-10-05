"""
Módulo principal da assistente Chico.
Contém a classe Chico que orquestra todos os comandos.
"""

import logging
import speech_recognition as sr

from agenda import Agenda
from calculadora import Calculadora
from clima import Clima
from desktop import Desktop
from financas import Financas
from ia_generativa import IAGenerativa
from face import ReconhecimentoFacial
from midia import Midia
from notas import Notas
from extras import Extras
from rotinas import Rotinas
from roteador import Roteador
from sistema import Sistema
from tts import TTS
from visao import Visao

logger = logging.getLogger(__name__)

# Nome de ativação da assistente
NOME_ASSISTENTE = "chico"
ALIASES_ATIVACAO = {"chico", "tchico", "chicos"}  # variações de pronúncia


class Chico:
    """
    Assistente virtual Chico.

    Gerencia o ciclo de escuta → interpretação → execução de comandos de voz.
    Só executa ações após ser ativada pelo nome.
    """

    def __init__(self) -> None:
        """Inicializa todos os módulos e configura voz/microfone."""
        logger.info("Inicializando Chico...")

        # Reconhecimento de voz
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8  # aguarda pausas de 0.8s
        self.recognizer.energy_threshold = 300

        # Síntese de voz (neural + fallback do sistema)
        self._tts = TTS()

        # Módulos de funcionalidade
        self.agenda = Agenda()
        self.calculadora = Calculadora()
        self.clima = Clima()
        self.financas = Financas()
        self.ia = IAGenerativa()
        self.face = ReconhecimentoFacial()
        self.midia = Midia()
        self.sistema = Sistema()
        # Extras cross-platform: detecta Windows/Mac no __init__ e faz retry
        self.extras = Extras()

        # Tier 1 — modulos novos que orquestram os ja existentes (injecao de dependencia)
        self.rotinas = Rotinas(self.extras, self.midia, self.agenda, self.sistema, self.clima, self.financas)
        self.visao = Visao(self.extras, self.ia)
        self.desktop = Desktop(self.ia)
        self.notas = Notas(self.ia)

        # Roteador por embeddings — remove a determinicidade dos if "palavra" in instrucao
        # Usa TF-IDF offline por padrao; para embeddings reais do Gemini, passe usar_gemini=True
        # (precisa de GEMINI_API_KEY e descomentar o bloco em roteador.py:_vetorizar)
        self.roteador = Roteador()

        logger.info("Chico pronto!")

    # ------------------------------------------------------------------ #
    #  VOZ                                                                 #
    # ------------------------------------------------------------------ #

    def falar(self, texto: str) -> None:
        """Sintetiza voz e imprime o texto no console."""
        print(f"\n🤖 Chico: {texto}")
        self._tts.falar(texto)

    # ------------------------------------------------------------------ #
    #  ESCUTA                                                              #
    # ------------------------------------------------------------------ #

    def ouvir(self, prompt: str = "Ouvindo...") -> str:
        """
        Captura áudio do microfone e retorna o texto reconhecido.

        Args:
            prompt: mensagem exibida enquanto aguarda o usuário falar.

        Returns:
            Texto reconhecido em minúsculas, ou string vazia em caso de falha.
        """
        print(f"\n🎙️  {prompt}")
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=10)
            texto = self.recognizer.recognize_google(audio, language="pt-BR")
            texto = texto.lower().strip()
            print(f"   ✅ Reconhecido: '{texto}'")
            return texto
        except sr.WaitTimeoutError:
            logger.debug("Timeout ao aguardar fala.")
            return ""
        except sr.UnknownValueError:
            logger.debug("Fala não reconhecida.")
            return ""
        except sr.RequestError as exc:
            logger.error("Erro no serviço de reconhecimento: %s", exc)
            return ""

    def ouvir_ou_digitar(self, prompt: str = "Ouvindo...") -> str:
        """
        Permite que o usuário fale ou digite o comando (útil para testes).

        Returns:
            Comando em minúsculas.
        """
        digitado = input(f"\n⌨️  Digite o comando (Enter para usar voz): ").strip()
        if digitado:
            return digitado.lower()
        return self.ouvir(prompt)

    # ------------------------------------------------------------------ #
    #  ROTEAMENTO DE COMANDOS                                              #
    # ------------------------------------------------------------------ #

    def _ativada(self, comando: str) -> bool:
        """
        Verifica se o comando contém o nome de ativação da assistente.

        Args:
            comando: texto reconhecido pelo microfone.

        Returns:
            True se Chico foi chamado pelo nome.
        """
        return any(alias in comando for alias in ALIASES_ATIVACAO)

    def _extrair_instrucao(self, comando: str) -> str:
        """
        Remove o nome da assistente do comando, retornando só a instrução.

        Args:
            comando: texto completo do usuário.

        Returns:
            Instrução limpa sem o nome da assistente.
        """
        for alias in ALIASES_ATIVACAO:
            comando = comando.replace(alias, "").strip()
        # Tira pontuação residual das bordas (ex.: "chico, anota isso" -> ", anota isso")
        return comando.strip(" ,;:.!?-")

    def _processar_comando(self, instrucao: str) -> bool:
        """
        Roteia a instrução para o módulo correto via embeddings.

        Fluxo:
          1) O roteador vetoriza a instrucao e acha o intent mais proximo (cosseno).
          2) Se o score ficar abaixo do limiar, cai no fallback da IA generativa.
          3) Cada intent mapeia para o mesmo handler de antes — so mudou o "if".
        Args:
            instrucao: comando já sem o nome da assistente.

        Returns:
            False se o usuário pediu para encerrar, True caso contrário.
        """
        # Roteamento por embeddings (TF-IDF offline por padrao)
        intent, score, _ = self.roteador.rotear(instrucao)
        logger.debug("Roteamento: '%s' -> %s (%.2f)", instrucao[:50], intent, score)

        # Se nao reconheceu nenhum intent, deixa a IA responder (fallback nao-deterministico)
        if intent is None:
            # Mas ainda checa saudacao/encerrar por fallback simples para nao gastar IA
            if not instrucao.strip():
                self.falar("Olá! Como posso ajudar?")
                return True
            self.falar("Não reconheci esse comando. Consultando a IA...")
            resposta = self.ia.perguntar(instrucao)
            self.falar(resposta)
            return True

        # ── AGENDA ──────────────────────────────────────────────────────
        if intent == "cadastrar_agenda":
            self.falar("Ok! Qual evento devo cadastrar?")
            evento = self.ouvir_ou_digitar("Aguardando o nome do evento...")
            if evento:
                self.agenda.cadastrar_evento(evento)
                self.falar(f"Evento '{evento}' cadastrado com sucesso!")
            else:
                self.falar("Não entendi o evento. Tente novamente.")

        elif intent == "ler_agenda":
            eventos = self.agenda.ler_eventos()
            if eventos:
                self.falar(f"Você tem {len(eventos)} evento(s) na agenda:")
                for i, ev in enumerate(eventos, 1):
                    self.falar(f"{i}: {ev}")
            else:
                self.falar("Sua agenda está vazia.")

        elif intent == "limpar_agenda":
            self.agenda.limpar_agenda()
            self.falar("Agenda limpa com sucesso!")

        # ── TEMPO / DATA ─────────────────────────────────────────────────
        elif intent == "hora":
            hora = self.sistema.hora_atual()
            self.falar(f"São {hora}.")

        elif intent == "data":
            dia = self.sistema.dia_atual()
            self.falar(f"Hoje é {dia}.")

        # ── CALCULAR ─────────────────────────────────────────────────────
        elif intent == "calcular":
            # Remove palavra "calcular/calcule" se existir, senao usa a frase toda (ex: "quanto e dez mais cinco")
            expressao = instrucao.replace("calcular", "").replace("calcule", "").strip()
            if not expressao:
                self.falar("Qual operação devo calcular?")
                expressao = self.ouvir_ou_digitar("Diga a operação...")
            # Se ainda nao tem operador, tenta usar a instrucao original completa
            if expressao == instrucao.replace("calcular", "").replace("calcule", "").strip() and "mais" not in expressao and "menos" not in expressao and "vezes" not in expressao:
                expressao = instrucao
            resultado = self.calculadora.calcular(expressao)
            self.falar(resultado)

        # ── RECONHECIMENTO FACIAL ─────────────────────────────────────────
        elif intent == "cadastrar_rosto":
            self.falar("Qual é o seu nome?")
            nome = self.ouvir_ou_digitar("Diga o nome para cadastrar...")
            if not nome:
                self.falar("Não entendi o nome. Tente novamente.")
            else:
                self.falar(f"Olhe para a câmera, {nome}. Vou tirar algumas fotos.")
                resultado = self.face.cadastrar(nome)
                self.falar(resultado)

        elif intent == "reconhecer_face":
            self.falar("Abrindo a câmera para reconhecimento facial...")
            nome = self.face.reconhecer()
            self.falar(f"Reconheci: {nome}")

        # ── IA GENERATIVA (Gemini) ────────────────────────────────────────
        elif intent == "ia_generativa":
            self.falar("Consultando a IA. Um momento...")
            resposta = self.ia.perguntar(instrucao)
            self.falar(resposta)

        # ── EXTRAS: CLIMA ─────────────────────────────────────────────────
        elif intent == "clima":
            cidade = self.clima.extrair_cidade(instrucao) or "São Paulo"
            self.falar(f"Verificando o clima em {cidade}...")
            previsao = self.clima.buscar_previsao(cidade)
            self.falar(previsao)

        # ── EXTRAS: FINANÇAS ──────────────────────────────────────────────
        elif intent == "dolar":
            cotacao = self.financas.cotacao_dolar()
            self.falar(cotacao)

        elif intent == "bitcoin":
            btc = self.financas.cotacao_bitcoin()
            self.falar(btc)

        # ── EXTRAS: MÍDIA ─────────────────────────────────────────────────
        elif intent == "controle_midia":
            # Decide a acao pelo conteudo da frase (pausar/proxima/anterior/continuar)
            low = instrucao.lower()
            if any(p in low for p in ("pausar", "pause", "parar")):
                self.falar(self.midia.pausar())
            elif any(p in low for p in ("proxima", "próxima", "pula", "pular")):
                self.falar(self.midia.proxima())
            elif any(p in low for p in ("anterior", "voltar", "volta")):
                self.falar(self.midia.anterior())
            else:
                self.falar(self.midia.continuar())

        elif intent == "tocar_musica":
            musica = (
                instrucao.replace("tocar", "")
                .replace("música", "")
                .replace("musica", "")
                .replace("no spotify", "")
                .replace("spotify", "")
                .strip()
            )
            if not musica:
                self.falar("Qual música devo tocar?")
                musica = self.ouvir_ou_digitar("Nome da música...")
            self.falar(self.midia.tocar_spotify(musica))

        elif intent == "pesquisar":
            termo = instrucao.replace("pesquisar", "").replace("pesquisa", "").replace("no google", "").replace("google", "").strip()
            if not termo:
                self.falar("O que devo pesquisar?")
                termo = self.ouvir_ou_digitar("O que pesquisar...")
            self.midia.pesquisar_google(termo)
            self.falar(f"Pesquisando '{termo}' no Google!")

        # ── EXTRAS ITEM 10 (cross-platform: detecta Windows/Mac e faz retry) ─
        elif intent == "volume":
            self.falar(self.extras.volume(instrucao))

        elif intent == "screenshot":
            self.falar(self.extras.screenshot())

        elif intent == "youtube":
            self.falar(self.extras.youtube(instrucao))

        elif intent == "portal_faculdade":
            self.falar(self.extras.portal_faculdade())

        # ── TIER 1: ROTINAS (1 frase -> varias acoes) ───────────────────────
        elif intent == "rotina":
            for mensagem in self.rotinas.despachar(instrucao):
                self.falar(mensagem)

        # ── TIER 1: VISÃO (tela e câmera descritas pelo Gemini) ─────────────
        elif intent == "ver_tela":
            self.falar("Deixa eu ver sua tela...")
            self.falar(self.visao.ver_tela())

        elif intent == "descrever_cena":
            self.falar("Olhando pela câmera...")
            self.falar(self.visao.descrever_cena())

        # ── TIER 1: DESKTOP (ações no PC) ───────────────────────────────────
        elif intent == "abrir_arquivo":
            self.falar(self.desktop.abrir_arquivo(instrucao))

        elif intent == "bloquear_tela":
            self.falar(self.desktop.bloquear_tela())

        elif intent == "desligar_pc":
            if any(p in instrucao for p in ("cancela", "cancelar", "desfaz")):
                self.falar(self.desktop.cancelar_desligamento())
            else:
                self.falar(self.desktop.agendar_desligamento(instrucao))

        elif intent == "clipboard":
            self.falar(self.desktop.clipboard())

        # ── TIER 1: NOTAS (caderno falado + leitura de PDF) ─────────────────
        elif intent == "anotar":
            ditado = self.notas.extrair_ditado(instrucao)
            if not ditado:
                self.falar("O que devo anotar?")
                ditado = self.ouvir_ou_digitar("Ditando a nota...")
            self.falar(self.notas.anotar(ditado))

        elif intent == "ler_notas":
            self.falar(self.notas.ler_notas())

        elif intent == "ler_pdf":
            self.falar("Deixa eu ler esse PDF...")
            self.falar(self.notas.ler_pdf(instrucao))

        # ── SAUDAÇÕES ─────────────────────────────────────────────────────
        elif intent == "saudacao":
            self.falar("Olá! Como posso ajudar?")

        # ── ENCERRAR ──────────────────────────────────────────────────────
        elif intent == "encerrar":
            self.falar("Até logo! Encerrando o sistema.")
            return False  # sinal para parar o loop principal

        # ── FALLBACK (nao deveria cair aqui, ja tratado no inicio) ──────
        else:
            self.falar("Consultando a IA...")
            resposta = self.ia.perguntar(instrucao)
            self.falar(resposta)

        return True

    # ------------------------------------------------------------------ #
    #  LOOP PRINCIPAL                                                      #
    # ------------------------------------------------------------------ #

    def iniciar(self) -> None:
        """
        Inicia o loop principal da assistente.

        A assistente só processa comandos após reconhecer o próprio nome.
        Se o nome não for detectado, apenas imprime o texto reconhecido.
        """
        self.falar("Sistema Chico inicializado. Diga 'Chico' para ativar.")
        print("\n" + "=" * 60)
        print("  C.H.I.C.O. — Assistente Virtual")
        print("  Diga 'Chico' para ativar | 'sair' para encerrar")
        print("=" * 60)

        continuar = True
        while continuar:
            try:
                comando = self.ouvir_ou_digitar("Aguardando ativação ('Chico')...")

                if not comando:
                    continue  # nenhuma entrada, aguarda novamente

                if self._ativada(comando):
                    instrucao = self._extrair_instrucao(comando)

                    # Se só falou o nome sem instrução, pede o comando
                    if not instrucao:
                        self.falar("Sim? O que deseja?")
                        instrucao = self.ouvir_ou_digitar("Qual o comando?")

                    if instrucao:
                        continuar = self._processar_comando(instrucao)
                else:
                    # Nome não detectado → imprime sem executar ação
                    print(f"   [sem ativação] Texto reconhecido: '{comando}'")

            except KeyboardInterrupt:
                print("\n\n⚡ Interrompido pelo usuário.")
                self.falar("Encerrando. Até logo!")
                break
