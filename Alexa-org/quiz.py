"""
Quiz — o Chico vira professor: "me faz um quiz da prova de sexta".

Fonte das perguntas, em ordem de prioridade:
1. "quiz sobre X"  -> tema livre, perguntas diretas do Gemini;
2. "quiz da prova" -> puxa eventos da agenda com "prova" e usa como tema;
3. sem tema        -> usa o caderno data/notas.md como conteúdo.

O módulo é puro: `preparar` devolve a lista de perguntas, `avaliar`
corrige cada resposta — quem conduz o diálogo (falar/ouvir) é o chico.py,
que já tem o loop de voz.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

NUM_PERGUNTAS = 3  # quiz falado: curto para não cansar


class Quiz:
    """Gera perguntas pela IA a partir do tema/agenda/notas e avalia respostas."""

    def __init__(self, ia, agenda, notas) -> None:
        """Recebe IAGenerativa, Agenda e Notas (fonte do conteúdo)."""
        self.ia = ia
        self.agenda = agenda
        self.notas = notas

    # ------------------------------------------------------------------ #
    #  FONTES                                                             #
    # ------------------------------------------------------------------ #

    def _fonte(self, instrucao: str) -> tuple[str, str]:
        """
        Decide tema e contexto do quiz a partir do comando.

        Returns:
            (tema, contexto) — contexto é o material de apoio opcional.
        """
        low = instrucao.lower()

        tema_explicito = re.search(r"\bsobre\s+(.+)", low)
        if tema_explicito:
            return tema_explicito.group(1).strip(" ,;:.!?-"), ""

        if "prova" in low:
            provas = [e for e in self.agenda.ler_eventos() if "prova" in e.lower()]
            if provas:
                return "as provas da agenda", "\n".join(provas[-5:])
            return "uma prova genérica", ""

        caderno = self.notas.texto_cru()
        if caderno:
            return "suas anotações", caderno[:3000]
        return "conhecimento geral", ""

    # ------------------------------------------------------------------ #
    #  JOGO                                                               #
    # ------------------------------------------------------------------ #

    def preparar(self, instrucao: str) -> tuple[list[str], str, str]:
        """
        Monta as perguntas do quiz.

        Returns:
            (perguntas, tema, erro) — perguntas vazias + erro preenchido
            quando não deu para montar.
        """
        tema, contexto = self._fonte(instrucao)
        prompt = (
            f"Gere {NUM_PERGUNTAS} perguntas curtas de quiz em português sobre "
            f"'{tema}'. Uma por linha, cada uma começando com 'Q:'. "
            "Não escreva o gabarito, nem numere."
        )
        if contexto:
            prompt += f"\n\nBaseie-se neste material:\n{contexto}"

        resposta = self.ia.perguntar(prompt)
        perguntas = [
            linha.split(":", 1)[1].strip()
            for linha in resposta.splitlines()
            if linha.strip().upper().startswith("Q:")
        ]
        if not perguntas:
            logger.warning("Gemini não gerou perguntas no formato Q: — resposta: %s", resposta[:120])
            return [], tema, (
                "Não consegui montar o quiz agora — a IA precisa estar "
                "configurada (GEMINI_API_KEY) para gerar perguntas."
            )
        return perguntas[:NUM_PERGUNTAS], tema, ""

    def avaliar(self, pergunta: str, resposta_aluno: str) -> tuple[str, bool]:
        """
        Corrige uma resposta falada.

        Returns:
            (comentário falável, acertou?)
        """
        veredito = self.ia.perguntar(
            "Você é um professor corrigindo um quiz. Pergunta: "
            f"'{pergunta}'. Resposta do aluno: '{resposta_aluno}'. "
            "Comece com CERTO ou ERRADO e explique em UMA frase."
        )
        acertou = veredito.strip().upper().startswith("CERTO")
        return veredito, acertou


if __name__ == "__main__":
    # Teste com IA fake determinística
    class _IAFake:
        def __init__(self):
            self.chamadas = []
        def perguntar(self, p):
            self.chamadas.append(p)
            if "Gere" in p:
                return "Q: Quanto é 2+2?\nQ: Capital do Brasil?\nQ: Cor do céu?\nQ: extra"
            return "CERTO, boa resposta."

    class _AgendaFake:
        def ler_eventos(self):
            return ["[01/01/2026 09:00] prova de cálculo sexta às 18h"]

    class _NotasFake:
        def texto_cru(self):
            return "## ideia\n- app de cantina"

    q = Quiz(_IAFake(), _AgendaFake(), _NotasFake())

    perguntas, tema, erro = q.preparar("me faz um quiz sobre python")
    assert tema == "python" and perguntas == ["Quanto é 2+2?", "Capital do Brasil?", "Cor do céu?"], (perguntas, tema)
    print("sobre ->", tema, perguntas)

    perguntas, tema, _ = q.preparar("me faz um quiz da prova")
    assert tema == "as provas da agenda" and perguntas
    print("prova ->", tema)

    comentario, acertou = q.avaliar("Quanto é 2+2?", "quatro")
    assert acertou and "CERTO" in comentario
    print("avaliar ->", comentario)
    print("quiz OK")
