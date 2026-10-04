"""
Rotinas — uma frase dispara várias ações (o "Alexa Routines" do Chico).

Cada rotina só orquestra métodos que já existem nos outros módulos:
- modo_foco: muta o volume, pausa o Spotify e registra na agenda
- modo_aula: abre o portal da FIAP e o YouTube (no tema, se dito) e registra
- bom_dia: briefing falado com data, hora, agenda, clima e dólar

As mensagens são devolvidas como lista para o chico.py falar uma a uma
(mesmo padrão do "ler agenda", que fala vários textos em sequência).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Frases que indicam o briefing da manhã dentro de um comando de rotina
GATILHOS_BOM_DIA = ("bom dia", "resumo do dia", "resumo da manhã", "briefing", "como está meu dia", "como esta meu dia")


class Rotinas:
    """Sequências de ações prontas disparadas por "modo X" ou "bom dia"."""

    def __init__(self, extras, midia, agenda, sistema, clima, financas) -> None:
        """Recebe os módulos já inicializados pelo Chico (injeção de dependência)."""
        self.extras = extras
        self.midia = midia
        self.agenda = agenda
        self.sistema = sistema
        self.clima = clima
        self.financas = financas

    def despachar(self, instrucao: str) -> list[str]:
        """
        Descobre qual rotina a frase pede e a executa.

        Args:
            instrucao: comando já sem o nome da assistente (ex.: "modo foco").

        Returns:
            Lista de mensagens para a assistente falar em sequência.
        """
        low = instrucao.lower()

        if any(gatilho in low for gatilho in GATILHOS_BOM_DIA):
            return self.bom_dia()

        tema = self._extrair_tema(low)
        if "foco" in low or "concentr" in low:
            return self.modo_foco()
        if "aula" in low or "estudo" in low or "estudar" in low:
            return self.modo_aula(tema)

        return [
            "Não conheço essa rotina. Os modos são: foco e aula "
            "(diga 'modo aula sobre cálculo' para já abrir um vídeo do tema). "
            "Também entendo 'bom dia' para o resumo da manhã."
        ]

    def modo_foco(self) -> list[str]:
        """Muta o som, pausa o Spotify e deixa registrado na agenda."""
        mensagens = [
            "Modo foco ativado.",
            self.extras.volume("mutar o volume"),
            self.midia.pausar(),
        ]
        self.agenda.cadastrar_evento("Sessão de foco iniciada")
        mensagens.append("Anotei na agenda que você entrou em foco. Bom trabalho!")
        return mensagens

    def modo_aula(self, tema: str = "") -> list[str]:
        """Abre o portal FIAP e o YouTube; com tema, já pesquisa um vídeo."""
        mensagens = [
            "Modo aula ativado.",
            self.extras.portal_faculdade(),
            self.extras.youtube(f"abre o youtube e toca um video sobre {tema}" if tema else "abre o youtube"),
        ]
        self.agenda.cadastrar_evento(f"Modo aula ativado{f' — tema: {tema}' if tema else ''}")
        mensagens.append("Registrei na agenda. Bons estudos!")
        return mensagens

    def bom_dia(self) -> list[str]:
        """Briefing da manhã: data, hora, agenda, clima e dólar em sequência."""
        mensagens = [
            f"Bom dia! Hoje é {self.sistema.dia_atual()} e são {self.sistema.hora_atual()}."
        ]

        eventos = self.agenda.ler_eventos()
        if eventos:
            mensagens.append(f"Você tem {len(eventos)} registro(s) na agenda:")
            mensagens.extend(eventos[-5:])  # só os 5 mais recentes para não enrolar
        else:
            mensagens.append("Sua agenda está vazia.")

        mensagens.append(self.clima.buscar_previsao("São Paulo"))
        mensagens.append(self.financas.cotacao_dolar())
        return mensagens

    @staticmethod
    def _extrair_tema(instrucao: str) -> str:
        """Extrai o tema de 'modo aula sobre X' (só a palavra 'sobre' marca o tema)."""
        match = re.search(r"\bsobre\s+(.+)", instrucao)
        return match.group(1).strip() if match else ""


if __name__ == "__main__":
    # Teste do despachante sem os módulos de verdade
    class _Fake:
        def __getattr__(self, nome):
            return lambda *a, **k: f"[fake {nome}]"

    r = Rotinas(_Fake(), _Fake(), _Fake(), _Fake(), _Fake(), _Fake())
    for frase in ("modo foco", "modo aula sobre python", "bom dia", "modo relaxar"):
        print(frase, "->", r.despachar(frase))
