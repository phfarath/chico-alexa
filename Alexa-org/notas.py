"""
Notas — o caderno falado do Chico.

- anotar: ditado -> Gemini titula/estrutura -> data/notas.md
- ler_notas: lê o arquivo (IA resume quando está longo)
- ler_pdf: extrai texto de um PDF (pypdf) -> Gemini resume -> fala

Reutiliza o padrão de persistência de agenda.py (data/ + append com timestamp)
e o fuzzy finder de desktop.py para localizar o PDF pelo nome falado.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from desktop import buscar_arquivo

logger = logging.getLogger(__name__)

# Arquivos ficam relativos a este módulo (mesmo critério de face.py)
RAIZ = Path(__file__).resolve().parent
NOTAS_PATH = RAIZ / "data" / "notas.md"

# Palavras de comando removidas do ditado ("anota uma ideia: X" -> "X")
PADRAO_GATILHOS_NOTA = re.compile(
    r"\b(anota|anote|anotar|anotando|registra|registrar|guarda|guardar|"
    r"faz|fazer|faça|uma ideia|essa ideia|essa|isso|aí|ai|pra mim|por favor)\b"
)
# Palavras de comando removidas do nome do PDF ("lê o pdf trabalho" -> "trabalho")
PADRAO_GATILHOS_PDF = re.compile(
    r"\b(lê|le|ler|leia|resume|resuma|resumir|resumo|abre|abrir|o|a|"
    r"pdf|arquivo|documento|trabalho|pra mim|por favor|esse|esse arquivo)\b"
)

# Limite de páginas e de caracteres enviados ao Gemini (resposta falável)
PAGINAS_MAX_PDF = 15
CHARS_MAX_RESUMO = 6000


class Notas:
    """Gerencia anotações pessoais e leitura de PDFs em voz alta."""

    def __init__(self, ia) -> None:
        """Recebe IAGenerativa para titular/resumir conteúdo."""
        self.ia = ia
        NOTAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not NOTAS_PATH.exists():
            NOTAS_PATH.touch()
            logger.info("Arquivo notas.md criado em %s", NOTAS_PATH)

    def extrair_ditado(self, instrucao: str) -> str:
        """
        Limpa o comando e devolve só o que deve ser anotado.

        Args:
            instrucao: comando (ex.: "anota uma ideia: app de cantina").

        Returns:
            Texto da nota, ou "" se o usuário só pediu para anotar.
        """
        texto = PADRAO_GATILHOS_NOTA.sub(" ", instrucao.lower())
        return " ".join(texto.split()).strip(" :.-")

    def anotar(self, texto: str) -> str:
        """
        Estrutura o ditado com a IA e apende em data/notas.md.

        Args:
            texto: conteúdo já limpo (ou o ditado cru se a IA falhar).

        Returns:
            Confirmação para falar.
        """
        if not texto.strip():
            return "Não entendi o que anotar. Tente de novo."

        corpo = self.ia.perguntar(
            "Transforme a anotação abaixo em uma nota curta e organizada em "
            "markdown (um título com ## e até 3 bullets). Responda SÓ a nota.\n\n"
            + texto
        )
        # Fallback: sem Gemini (ou erro) a nota ainda é salva — com o texto cru
        if corpo.startswith(("A IA generativa não", "Não consegui obter")):
            corpo = f"## Nota\n- {texto}"

        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(NOTAS_PATH, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"\n---\n*{timestamp}*\n\n{corpo}\n")
        logger.info("Nota registrada em %s", NOTAS_PATH)
        return "Anotado!"

    def ler_notas(self) -> str:
        """Lê as notas em voz alta; a IA resume quando o caderno está longo."""
        if not NOTAS_PATH.exists() or not NOTAS_PATH.read_text(encoding="utf-8").strip():
            return "Você ainda não tem notas. Diga 'anota uma ideia' para começar."

        conteudo = NOTAS_PATH.read_text(encoding="utf-8").strip()
        if len(conteudo) > 1500:
            return self.ia.perguntar(
                "Resuma em até 4 frases as anotações abaixo, como quem conta "
                f"rapidamente o que foi registrado:\n\n{conteudo[:4000]}"
            )
        # Limpa a marcação markdown para soar natural falado
        limpo = re.sub(r"[#*>\-]+", " ", conteudo)
        limpo = " ".join(limpo.split())
        return f"Você anotou: {limpo[:1200]}"

    def ler_pdf(self, instrucao: str) -> str:
        """
        Localiza um PDF pelo nome falado, extrai o texto e resume com a IA.

        Args:
            instrucao: comando (ex.: "lê o pdf do trabalho final").

        Returns:
            Resumo falado, ou mensagem do que faltou.
        """
        termo = PADRAO_GATILHOS_PDF.sub(" ", instrucao.lower())
        termo = " ".join(termo.split()).strip()

        caminho = buscar_arquivo(termo, extensoes={".pdf"}) if termo else self._pdf_mais_recente()
        if caminho is None:
            return (
                "Não achei o PDF em Documents, Desktop ou Downloads. "
                "Diga o nome do arquivo, ex.: 'lê o pdf do trabalho final'."
            )

        texto = self._extrair_texto_pdf(caminho)
        if texto is None:
            return "Para ler PDF preciso do pypdf: pip install pypdf"
        if not texto.strip():
            return f"O PDF {caminho.name} não tem texto extraível — pode ser um documento escaneado."

        return self.ia.perguntar(
            f"Resuma em até 5 frases o conteúdo do documento '{caminho.name}', "
            f"como quem explica o essencial para alguém:\n\n{texto[:CHARS_MAX_RESUMO]}"
        )

    @staticmethod
    def _pdf_mais_recente() -> Path | None:
        """Sem nome falado, usa o PDF modificado por último nas pastas comuns."""
        mais_recente: Path | None = None
        for pasta in ("Documents", "Desktop", "Downloads"):
            raiz = Path.home() / pasta
            if not raiz.exists():
                continue
            try:
                for pdf in raiz.rglob("*.pdf"):
                    if mais_recente is None or pdf.stat().st_mtime > mais_recente.stat().st_mtime:
                        mais_recente = pdf
            except OSError:
                continue
        return mais_recente

    @staticmethod
    def _extrair_texto_pdf(caminho: Path) -> str | None:
        """Extrai texto com pypdf (fallback PyPDF2). None = leitor indisponível."""
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            try:
                from PyPDF2 import PdfReader  # type: ignore
            except ImportError:
                logger.debug("Nem pypdf nem PyPDF2 instalados")
                return None
        try:
            reader = PdfReader(str(caminho))
            partes = [pagina.extract_text() or "" for pagina in reader.pages[:PAGINAS_MAX_PDF]]
            return "\n".join(partes)
        except Exception as exc:
            logger.error("Falha ao extrair texto de %s: %s", caminho, exc)
            return ""


if __name__ == "__main__":
    # Teste rápido sem assistente:
    #   python notas.py
    class _FakeIA:
        def perguntar(self, texto):
            return f"[ia geraria: {texto[:50]}...]"

    n = Notas(_FakeIA())
    print(repr(n.extrair_ditado("anota uma ideia: app de cantina com fila virtual")))
    print(repr(n.extrair_ditado("anota isso")))
    print(n.anotar("ideia de app de cantina com fila virtual"))
    print(n.ler_notas())
