"""
Desktop — o Chico mexendo no PC de verdade.

- abrir_arquivo: busca fuzzy em Documents/Desktop/Downloads e abre o melhor match
- bloquear_tela: trava a sessão (Windows / Mac / Linux)
- agendar_desligamento / cancelar_desligamento
- clipboard: lê a área de transferência e resume com a IA

Mesmo padrão do extras.py: detecta o SO no __init__, tenta o nativo com
fallbacks e devolve mensagem honesta se nada funcionar.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from extras import _plataforma

logger = logging.getLogger(__name__)

# Pastas da home vasculhadas por "abre meu trabalho" / "lê o pdf X"
PASTAS_BUSCA = ("Documents", "Desktop", "Downloads")
# Arquivos temporários/parciais que não vale abrir
EXTENSOES_IGNORADAS = {".tmp", ".part", ".crdownload", ".download", ".ds_store"}
# Score mínimo de similaridade (0-1) para aceitar um arquivo como match
SCORE_MINIMO = 0.35
# Teto de arquivos indexados por busca (a casa pode ser enorme)
MAX_CANDIDATOS = 20000

# Comandos de bloqueio por plataforma, tentados em ordem
COMANDOS_LOCK = {
    "windows": [["rundll32.exe", "user32.dll,LockWorkStation"]],
    "mac": [["pmset", "displaysleepnow"]],
    "linux": [
        ["loginctl", "lock-session"],
        ["xdg-screensaver", "lock"],
        ["gnome-screensaver-command", "--lock"],
    ],
}

# Palavras que só fazem parte do pedido, não do nome do arquivo
PADRAO_GATILHOS_ARQUIVO = re.compile(
    r"\b(abre|abra|abrir|procura|procurar|busca|buscar|achar|ache|encontra|"
    r"encontrar|o|a|meu|minha|arquivo|documento|pasta|pra|para|por favor|"
    r"por gentileza|mim|de)\b"
)


def _termo_busca(instrucao: str) -> str:
    """Remove as palavras de comando; sobra só o nome do arquivo procurado."""
    termo = PADRAO_GATILHOS_ARQUIVO.sub(" ", instrucao.lower())
    return " ".join(termo.split()).strip(" ,;:.!?-")


def buscar_arquivo(termo: str, extensoes: set[str] | None = None) -> Path | None:
    """
    Procura fuzzy por um arquivo nas pastas comuns da home.

    Args:
        termo: parte do nome (ex.: "trabalho final", "planilha notas").
        extensoes: se dada, só considera arquivos com esses sufixos (ex.: {".pdf"}).

    Returns:
        Path do melhor match ou None.
    """
    if not termo:
        return None
    home = Path.home()
    candidatos: list[Path] = []
    for pasta in PASTAS_BUSCA:
        raiz = home / pasta
        if not raiz.exists():
            continue
        try:
            for caminho in raiz.rglob("*"):
                if len(candidatos) >= MAX_CANDIDATOS:
                    break
                if not caminho.is_file():
                    continue
                sufixo = caminho.suffix.lower()
                if sufixo in EXTENSOES_IGNORADAS:
                    continue
                if extensoes and sufixo not in extensoes:
                    continue
                candidatos.append(caminho)
        except OSError as exc:
            logger.debug("Não consegui varrer %s: %s", raiz, exc)

    melhor: Path | None = None
    melhor_score = 0.0
    termo_norm = termo.lower()
    for caminho in candidatos:
        stem = caminho.stem.lower()
        # Conteúdo exato do termo no nome vale mais que similaridade difusa
        if termo_norm in stem:
            score = 1.0 + len(termo_norm) / max(len(stem), 1)
        else:
            score = difflib.SequenceMatcher(None, termo_norm, stem).ratio()
        if score > melhor_score:
            melhor = caminho
            melhor_score = score

    if melhor is None or melhor_score < SCORE_MINIMO:
        logger.info("Nenhum arquivo com score >= %.2f para '%s' (melhor=%s %.2f)",
                    SCORE_MINIMO, termo, melhor, melhor_score)
        return None
    logger.info("Arquivo encontrado: %s (score %.2f)", melhor, melhor_score)
    return melhor


def _abrir_caminho(caminho: Path) -> bool:
    """Abre um arquivo/pasta no aplicativo padrão do sistema."""
    try:
        if sys.platform == "win32":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            return subprocess.run(["open", str(caminho)], timeout=10).returncode == 0
        if shutil.which("xdg-open"):
            return subprocess.run(
                ["xdg-open", str(caminho)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            ).returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Falha ao abrir %s: %s", caminho, exc)
    return False


class Desktop:
    """Ações diretas no computador: arquivos, bloqueio, energia, clipboard."""

    def __init__(self, ia) -> None:
        """Recebe IAGenerativa para resumir conteúdo (clipboard, etc.)."""
        self.ia = ia
        self.plataforma = _plataforma()
        logger.info("Desktop inicializado na plataforma: %s", self.plataforma)

    # Arquivos

    def abrir_arquivo(self, instrucao: str) -> str:
        """
        Busca fuzzy pelo nome falado e abre o arquivo.

        Args:
            instrucao: comando completo (ex.: "abre meu trabalho de faculdade").

        Returns:
            Mensagem para a assistente falar.
        """
        termo = _termo_busca(instrucao)
        if not termo:
            return "Qual arquivo devo abrir? Diga algo como 'abre meu trabalho'."
        caminho = buscar_arquivo(termo)
        if caminho is None:
            return f"Não achei nenhum arquivo parecido com '{termo}' em Documents, Desktop ou Downloads."
        if _abrir_caminho(caminho):
            return f"Abri {caminho.name}."
        return f"Achei {caminho.name} em {caminho.parent}, mas não consegui abrir neste sistema."

    # Bloqueio de tela

    def bloquear_tela(self) -> str:
        """Trava a sessão usando o comando nativo do SO."""
        for comando in COMANDOS_LOCK.get(self.plataforma, COMANDOS_LOCK["linux"]):
            try:
                if shutil.which(comando[0]) is None and self.plataforma != "windows":
                    continue
                resultado = subprocess.run(
                    comando, capture_output=True, timeout=10, check=False
                )
                if resultado.returncode == 0:
                    return "Tela bloqueada."
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("Comando de bloqueio %s falhou: %s", comando, exc)
        if self.plataforma == "windows":
            return "Não consegui bloquear a tela no Windows."
        if self.plataforma == "mac":
            return "Não consegui bloquear a tela no Mac. Verifique a permissão de automação."
        return "Não consegui bloquear a tela. Tente loginctl ou xdg-screensaver."

    # Energia

    def agendar_desligamento(self, instrucao: str) -> str:
        """
        Agenda o desligamento daqui a N minutos (ou horas).

        Args:
            instrucao: comando (ex.: "agenda desligamento em 30 minutos").

        Returns:
            Confirmação ou instrução do que faltou.
        """
        minutos = self._extrair_minutos(instrucao)
        if minutos <= 0:
            return "Em quanto tempo devo desligar? Diga algo como 'em 30 minutos' ou 'em uma hora'."

        if self.plataforma == "windows":
            segundos = minutos * 60
            try:
                resultado = subprocess.run(
                    ["shutdown", "/s", "/t", str(segundos)],
                    capture_output=True, timeout=10, check=False,
                )
                if resultado.returncode == 0:
                    return (
                        f"Desligamento agendado para daqui a {minutos} minutos. "
                        "Diga 'cancelar desligamento' para desfazer."
                    )
            except (OSError, subprocess.SubprocessError) as exc:
                logger.warning("Falha ao agendar desligamento no Windows: %s", exc)
            return "Não consegui agendar o desligamento no Windows."

        # Mac/Linux: shutdown -h +N precisa de root
        if shutil.which("shutdown"):
            try:
                resultado = subprocess.run(
                    ["shutdown", "-h", f"+{minutos}"],
                    capture_output=True, timeout=10, check=False,
                )
                if resultado.returncode == 0:
                    return f"Desligamento agendado para daqui a {minutos} minutos."
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("shutdown falhou: %s", exc)
        return (
            "No Mac/Linux agendar desligamento precisa de administrador. "
            f"Rode no terminal: sudo shutdown -h +{minutos}"
        )

    def cancelar_desligamento(self) -> str:
        """Desfaz um desligamento agendado."""
        if self.plataforma == "windows":
            try:
                resultado = subprocess.run(
                    ["shutdown", "/a"], capture_output=True, timeout=10, check=False
                )
                if resultado.returncode == 0:
                    return "Desligamento cancelado."
            except (OSError, subprocess.SubprocessError) as exc:
                logger.warning("Falha ao cancelar desligamento no Windows: %s", exc)
            return "Não consegui cancelar no Windows — talvez não houvesse desligamento agendado."
        return (
            "No Mac/Linux o cancelamento precisa de administrador. "
            "Rode no terminal: sudo killall shutdown"
        )

    # Clipboard

    def clipboard(self) -> str:
        """Lê a área de transferência e resume o conteúdo com a IA."""
        texto = self._ler_clipboard()
        if texto is None:
            return (
                "Não consegui ler a área de transferência. "
                "Instale pyperclip (pip install pyperclip) ou xclip no Linux."
            )
        if not texto.strip():
            return "A área de transferência está vazia."
        return self.ia.perguntar(
            "Resuma em uma frase o que este texto copiado para a área de "
            f"transferência contém:\n\n{texto[:2000]}"
        )

    def _ler_clipboard(self) -> str | None:
        """Tenta pyperclip, depois comandos nativos do SO. None = tudo falhou."""
        try:
            import pyperclip  # type: ignore

            return pyperclip.paste()
        except Exception:
            logger.debug("pyperclip indisponível, tentando comandos nativos")

        comandos: list[list[str]] = []
        if self.plataforma == "mac":
            comandos = [["pbpaste"]]
        elif self.plataforma == "windows":
            comandos = [["powershell", "-NoProfile", "-Command", "Get-Clipboard"]]
        else:
            comandos = [
                ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"],
                ["wl-paste"],
            ]
        for comando in comandos:
            try:
                if shutil.which(comando[0]) is None:
                    continue
                resultado = subprocess.run(
                    comando, capture_output=True, text=True, timeout=10, check=False
                )
                if resultado.returncode == 0:
                    return resultado.stdout
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("Clipboard via %s falhou: %s", comando[0], exc)
        return None

    @staticmethod
    def _extrair_minutos(instrucao: str) -> int:
        """Extrai o tempo de 'em 30 minutos' / 'em 2 horas' / 'em meia hora'."""
        low = instrucao.lower()
        if "meia hora" in low:
            return 30
        match = re.search(r"(\d+)\s*(horas?|h|minutos?|mins?)", low)
        if match:
            valor = int(match.group(1))
            unidade = match.group(2)
            return valor * 60 if unidade.startswith("h") else valor
        match = re.search(r"\b(uma|duas|três|tres)\s+horas?\b", low)
        if match:
            extensas = {"uma": 1, "duas": 2, "três": 3, "tres": 3}
            return extensas[match.group(1)] * 60
        return 0


if __name__ == "__main__":
    # Teste rápido sem assistente:
    #   python desktop.py
    class _FakeIA:
        def perguntar(self, texto):
            return f"[ia resumiria: {texto[:60]}...]"

    d = Desktop(_FakeIA())
    print("Plataforma:", d.plataforma)
    print(d._extrair_minutos("agenda desligamento em 30 minutos"), "min")
    print(d._extrair_minutos("desliga o pc em 2 horas"), "min")
    print(d._extrair_minutos("desliga em meia hora"), "min")
    print(repr(_termo_busca("abre meu trabalho de faculdade por favor")))
