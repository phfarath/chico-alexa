"""
Módulo principal da assistente Chico.
Contém a classe Chico que orquestra todos os comandos.
"""

import logging
import speech_recognition as sr

from agenda import Agenda
from calculadora import Calculadora
from clima import Clima
from financas import Financas
from ia_generativa import IAGenerativa
from face import ReconhecimentoFacial
from midia import Midia
from sistema import Sistema
from tts import TTS

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
        return comando

    def _processar_comando(self, instrucao: str) -> bool:
        """
        Roteia a instrução para o módulo correto.

        Args:
            instrucao: comando já sem o nome da assistente.

        Returns:
            False se o usuário pediu para encerrar, True caso contrário.
        """

        # ── AGENDA ──────────────────────────────────────────────────────
        if "cadastrar" in instrucao and "agenda" in instrucao:
            self.falar("Ok! Qual evento devo cadastrar?")
            evento = self.ouvir_ou_digitar("Aguardando o nome do evento...")
            if evento:
                self.agenda.cadastrar_evento(evento)
                self.falar(f"Evento '{evento}' cadastrado com sucesso!")
            else:
                self.falar("Não entendi o evento. Tente novamente.")

        elif "ler" in instrucao and "agenda" in instrucao:
            eventos = self.agenda.ler_eventos()
            if eventos:
                self.falar(f"Você tem {len(eventos)} evento(s) na agenda:")
                for i, ev in enumerate(eventos, 1):
                    self.falar(f"{i}: {ev}")
            else:
                self.falar("Sua agenda está vazia.")

        elif "limpar" in instrucao and "agenda" in instrucao:
            self.agenda.limpar_agenda()
            self.falar("Agenda limpa com sucesso!")

        # ── TEMPO / DATA ─────────────────────────────────────────────────
        elif "horas" in instrucao or "que horas" in instrucao:
            hora = self.sistema.hora_atual()
            self.falar(f"São {hora}.")

        elif "dia" in instrucao and "hoje" in instrucao:
            dia = self.sistema.dia_atual()
            self.falar(f"Hoje é {dia}.")

        # ── CALCULAR ─────────────────────────────────────────────────────
        elif "calcul" in instrucao:
            expressao = instrucao.replace("calcular", "").replace("calcule", "").strip()
            if not expressao:
                self.falar("Qual operação devo calcular?")
                expressao = self.ouvir_ou_digitar("Diga a operação...")
            resultado = self.calculadora.calcular(expressao)
            self.falar(resultado)

        # ── RECONHECIMENTO FACIAL ─────────────────────────────────────────
        elif "cadastrar" in instrucao and ("rosto" in instrucao or "face" in instrucao):
            self.falar("Qual é o seu nome?")
            nome = self.ouvir_ou_digitar("Diga o nome para cadastrar...")
            if not nome:
                self.falar("Não entendi o nome. Tente novamente.")
            else:
                self.falar(f"Olhe para a câmera, {nome}. Vou tirar algumas fotos.")
                resultado = self.face.cadastrar(nome)
                self.falar(resultado)

        elif "reconhecer face" in instrucao or "quem sou eu" in instrucao or "reconhecer rosto" in instrucao:
            self.falar("Abrindo a câmera para reconhecimento facial...")
            nome = self.face.reconhecer()
            self.falar(f"Reconheci: {nome}")

        # ── IA GENERATIVA (Gemini) ────────────────────────────────────────
        elif "pergunta" in instrucao or "me fala sobre" in instrucao or "o que é" in instrucao or "explica" in instrucao:
            self.falar("Consultando a IA. Um momento...")
            pergunta = instrucao
            resposta = self.ia.perguntar(pergunta)
            self.falar(resposta)

        # ── EXTRAS: CLIMA ─────────────────────────────────────────────────
        elif "previsão" in instrucao or "tempo" in instrucao or "clima" in instrucao:
            # Tenta extrair a cidade mencionada
            cidade = self.clima.extrair_cidade(instrucao) or "São Paulo"
            self.falar(f"Verificando o clima em {cidade}...")
            previsao = self.clima.buscar_previsao(cidade)
            self.falar(previsao)

        # ── EXTRAS: FINANÇAS ──────────────────────────────────────────────
        elif "dólar" in instrucao or "dollar" in instrucao or "câmbio" in instrucao:
            cotacao = self.financas.cotacao_dolar()
            self.falar(cotacao)

        elif "bitcoin" in instrucao or "btc" in instrucao or "cripto" in instrucao:
            btc = self.financas.cotacao_bitcoin()
            self.falar(btc)

        # ── EXTRAS: MÍDIA ─────────────────────────────────────────────────
        elif any(p in instrucao for p in ("pausar", "pause", "parar a música", "parar a musica")):
            self.falar(self.midia.pausar())

        elif "próxima" in instrucao or "proxima" in instrucao or "pula" in instrucao:
            self.falar(self.midia.proxima())

        elif "anterior" in instrucao or "volta a música" in instrucao or "volta a musica" in instrucao:
            self.falar(self.midia.anterior())

        elif any(p in instrucao for p in ("continuar", "retomar", "despausar")):
            self.falar(self.midia.continuar())

        elif "tocar" in instrucao or "música" in instrucao or "musica" in instrucao:
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

        elif "pesquisar" in instrucao or "pesquisa" in instrucao:
            termo = instrucao.replace("pesquisar", "").replace("pesquisa", "").replace("no google", "").replace("google", "").strip()
            if not termo:
                self.falar("O que devo pesquisar?")
                termo = self.ouvir_ou_digitar("O que pesquisar...")
            self.midia.pesquisar_google(termo)
            self.falar(f"Pesquisando '{termo}' no Google!")

        # ── SAUDAÇÕES ─────────────────────────────────────────────────────
        elif "olá" in instrucao or "ola" in instrucao or "ei" == instrucao or instrucao == "":
            self.falar("Olá! Como posso ajudar?")

        elif "como você está" in instrucao or "tudo bem" in instrucao:
            self.falar("Estou funcionando perfeitamente! E você?")

        # ── ENCERRAR ──────────────────────────────────────────────────────
        elif "tchau" in instrucao or "sair" in instrucao or "encerrar" in instrucao:
            self.falar("Até logo! Encerrando o sistema.")
            return False  # sinal para parar o loop principal

        # ── COMANDO NÃO RECONHECIDO → IA como fallback ───────────────────
        else:
            self.falar("Não reconheci esse comando. Consultando a IA...")
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
