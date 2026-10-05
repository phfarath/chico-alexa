"""
Agente — o Chico deixa de ser despachante e vira planejador.

Quando o roteador não reconhece um intent (ou a frase pede várias coisas
de uma vez, ex.: "me lembra da prova às 8 e vê o clima"), o Gemini recebe
as ferramentas abaixo como function declarations e devolve chamadas de
função. Cada chamada é executada no módulo correspondente e o resultado
volta ao modelo, que decide o próximo passo ou responde em texto.

Nada é reescrito: cada tool aponta para um método que já existe
(agenda.cadastrar_evento, clima.buscar_previsao, extras.youtube...).
Sem GEMINI_API_KEY o despachar devolve [] e o chico cai no fallback comum.
"""

from __future__ import annotations

import logging

from google import genai as google_genai

logger = logging.getLogger(__name__)

MODELO = "gemini-3.5-flash"
MAX_RODADAS = 6  # teto de chamadas de ferramenta por comando

SYSTEM_PROMPT_AGENTE = (
    "Você é Chico, um assistente virtual que age no computador do usuário. "
    "Quando o pedido envolver uma ação, chame a ferramenta correspondente — "
    "encadeie quantas forem precisas para pedidos compostos. "
    "Se nada se encaixar, responda diretamente em texto curto. "
    "Ao final, confirme em 1-2 frases o que fez, em português brasileiro."
)


def _fn(nome: str, descricao: str, propriedades: dict | None = None, obrigatorios: list[str] | None = None) -> dict:
    """Encurta a declaração de cada ferramenta (schema JSON do Gemini)."""
    declaracao: dict = {"name": nome, "description": descricao}
    if propriedades:
        declaracao["parameters"] = {
            "type": "object",
            "properties": {
                chave: {"type": "string", "description": desc}
                for chave, desc in propriedades.items()
            },
            "required": obrigatorios or list(propriedades),
        }
    return declaracao


# As ferramentas oferecidas ao Gemini — cada uma mapeia 1:1 um método já
# existente; a tabela _ferramentas() no __init__ liga nome -> callable.
DECLARACOES: list[dict] = [
    _fn("hora_atual", "Diz a hora atual."),
    _fn("dia_atual", "Diz a data de hoje por extenso."),
    _fn("clima", "Busca a previsão do tempo numa cidade.", {"cidade": "nome da cidade; se omitida, São Paulo"}, []),
    _fn("dolar", "Cotação atual do dólar em reais."),
    _fn("bitcoin", "Cotação atual do bitcoin."),
    _fn("agendar_na_agenda", "Registra um evento/lembrete na agenda do usuário.", {"evento": "texto do evento com dia e horário se houver"}),
    _fn("ler_agenda", "Lê os eventos registrados na agenda."),
    _fn("limpar_agenda", "Apaga TODOS os eventos da agenda. Só chame se o usuário pedir explicitamente."),
    _fn("tocar_musica", "Toca uma música no Spotify (ou abre a busca).", {"musica": "nome da música/artista"}),
    _fn("pausar_musica", "Pausa a música que está tocando."),
    _fn("continuar_musica", "Retoma a música pausada."),
    _fn("pesquisar_google", "Pesquisa um termo no Google.", {"termo": "o que pesquisar"}),
    _fn("abrir_youtube", "Abre o YouTube; com termo, já abre a busca/vídeo.", {"termo": "tema do vídeo, se houver"}, []),
    _fn("abrir_portal_faculdade", "Abre o portal do aluno da FIAP."),
    _fn("ajustar_volume", "Controla o volume do PC.", {"acao": "aumentar | diminuir | mutar | desmutar"}),
    _fn("tirar_print", "Tira um screenshot da tela e salva em arquivo."),
    _fn("anotar", "Salva uma anotação no caderno do usuário.", {"texto": "conteúdo da nota"}),
    _fn("ler_notas", "Lê as anotações salvas do usuário."),
    _fn("abrir_arquivo", "Procura um arquivo pelo nome em Documentos/Desktop/Downloads e abre.", {"nome": "parte do nome do arquivo"}),
    _fn("ler_clipboard", "Lê e resume o que está na área de transferência."),
    _fn("ver_tela", "Captura a tela e descreve o que está nela."),
    _fn("descrever_cena", "Fotografa pela webcam e descreve o ambiente."),
    _fn("calcular", "Calcula uma expressão matemática.", {"expressao": "ex.: '25 vezes 4' ou '10/3'"}),
]


class Agente:
    """Orquestra chamadas de ferramenta do Gemini sobre os módulos do Chico."""

    def __init__(self, ia, chico) -> None:
        """
        Args:
            ia: IAGenerativa (reuso do client Gemini já configurado).
            chico: instância Chico — as tools chamam seus módulos diretamente.
        """
        self.ia = ia
        self.chico = chico
        self._ferramentas = self._montar_ferramentas()

    def _montar_ferramentas(self) -> dict:
        """nome_da_tool -> callable que devolve a frase falada do resultado."""
        c = self.chico
        return {
            "hora_atual": lambda: f"São {c.sistema.hora_atual()}.",
            "dia_atual": lambda: f"Hoje é {c.sistema.dia_atual()}.",
            "clima": lambda cidade="São Paulo": c.clima.buscar_previsao(cidade or "São Paulo"),
            "dolar": lambda: c.financas.cotacao_dolar(),
            "bitcoin": lambda: c.financas.cotacao_bitcoin(),
            "agendar_na_agenda": self._agendar,
            "ler_agenda": self._ler_agenda,
            "limpar_agenda": self._limpar_agenda,
            "tocar_musica": lambda musica: c.midia.tocar_spotify(musica),
            "pausar_musica": lambda: c.midia.pausar(),
            "continuar_musica": lambda: c.midia.continuar(),
            "pesquisar_google": self._pesquisar,
            "abrir_youtube": lambda termo="": c.extras.youtube(f"abre o youtube e toca um video sobre {termo}" if termo else "abre o youtube"),
            "abrir_portal_faculdade": lambda: c.extras.portal_faculdade(),
            "ajustar_volume": lambda acao: c.extras.volume(f"{acao} o volume"),
            "tirar_print": lambda: c.extras.screenshot(),
            "anotar": lambda texto: c.notas.anotar(texto),
            "ler_notas": lambda: c.notas.ler_notas(),
            "abrir_arquivo": lambda nome: c.desktop.abrir_arquivo(f"abre {nome}"),
            "ler_clipboard": lambda: c.desktop.clipboard(),
            "ver_tela": lambda: c.visao.ver_tela(),
            "descrever_cena": lambda: c.visao.descrever_cena(),
            "calcular": lambda expressao: c.calculadora.calcular(expressao),
        }

    def _agendar(self, evento: str) -> str:
        self.chico.agenda.cadastrar_evento(evento)
        return f"Evento '{evento}' cadastrado na agenda."

    def _ler_agenda(self) -> str:
        eventos = self.chico.agenda.ler_eventos()
        if not eventos:
            return "A agenda está vazia."
        return f"Você tem {len(eventos)} evento(s): " + " | ".join(eventos[-8:])

    def _limpar_agenda(self) -> str:
        self.chico.agenda.limpar_agenda()
        return "Agenda limpa."

    def _pesquisar(self, termo: str) -> str:
        self.chico.midia.pesquisar_google(termo)
        return f"Pesquisei '{termo}' no Google."

    def despachar(self, instrucao: str) -> list[str]:
        """
        Manda a frase pro Gemini com as tools e executa o plano devolvido.

        Args:
            instrucao: comando livre do usuário (router não reconheceu intent).

        Returns:
            Lista de mensagens para falar, em ordem. [] se a IA estiver
            indisponível — o chamador cai no fallback comum.
        """
        if not self.ia._disponivel or self.ia._client is None:
            return []

        client = self.ia._client
        types = google_genai.types
        ferramenta = types.Tool(function_declarations=DECLARACOES)
        conteudo: list = [instrucao]
        mensagens: list[str] = []

        try:
            for _ in range(MAX_RODADAS):
                resposta = client.models.generate_content(
                    model=MODELO,
                    contents=conteudo,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT_AGENTE,
                        tools=[ferramenta],
                        # Desliga a execução automática do SDK: queremos falar
                        # o resultado de cada ação assim que ela acontece.
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                if not resposta.candidates:
                    break
                partes = resposta.candidates[0].content.parts or []
                chamadas = [p.function_call for p in partes if getattr(p, "function_call", None)]

                if not chamadas:
                    texto = (resposta.text or "").strip()
                    if texto:
                        mensagens.append(texto[:500] + ("..." if len(texto) > 500 else ""))
                    break

                # Repõe o turno do modelo e responde cada function_call
                conteudo.append(resposta.candidates[0].content)
                respostas_fn = []
                for chamada in chamadas:
                    resultado = self._executar(chamada.name, dict(chamada.args or {}))
                    mensagens.append(resultado)
                    respostas_fn.append(
                        types.Part.from_function_response(
                            name=chamada.name, response={"result": resultado}
                        )
                    )
                conteudo.append(types.Content(role="tool", parts=respostas_fn))
            else:
                mensagens.append("Consegui até aqui — o resto ficou grande demais pra uma frase só.")
        except Exception as exc:
            logger.error("Erro no planejador: %s", exc)
            if not mensagens:
                return []

        return mensagens

    def _executar(self, nome: str, args: dict) -> str:
        """Roda a tool escolhida pelo modelo; erro vira mensagem honesta."""
        funcao = self._ferramentas.get(nome)
        if funcao is None:
            logger.warning("Gemini pediu tool desconhecida: %s", nome)
            return f"Não conheço a ação '{nome}'."
        try:
            return str(funcao(**args))
        except TypeError:
            # Modelo mandou arg errado — tenta sem args como último recurso
            try:
                return str(funcao())
            except Exception as exc:
                logger.warning("Tool %s falhou: %s", nome, exc)
                return f"Não consegui executar '{nome}'."
        except Exception as exc:
            logger.warning("Tool %s falhou: %s", nome, exc)
            return f"Não consegui executar '{nome}'."


if __name__ == "__main__":
    # Teste do mapa de tools sem API: cada callable existe e responde string
    class _FakeIA:
        _disponivel = False
        _client = None

    class _FakeChico:
        def __getattr__(self, nome):
            return type("_M", (), {"__getattr__": lambda s, m: (lambda *a, **k: f"[{nome}.{m}]")})()

    a = Agente(_FakeIA(), _FakeChico())
    assert set(a._ferramentas) == {d["name"] for d in DECLARACOES}
    for nome in a._ferramentas:
        print(nome, "->", a._executar(nome, {}))
    assert a.despachar("teste") == []  # sem API key cai no fallback
    print("agente OK")
