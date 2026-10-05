"""
Módulo de gerenciamento de agenda.
Responsável por cadastrar, ler e limpar eventos no arquivo agenda.txt.
"""

import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

AGENDA_PATH = Path("data") / "agenda.txt"


class Agenda:
    """Gerencia eventos em arquivo de texto local (agenda.txt)."""

    def __init__(self, caminho: Path | None = None) -> None:
        """
        Garante que o diretório e o arquivo existam.

        Args:
            caminho: arquivo alternativo (perfis por rosto usam
                     data/perfis/<nome>/agenda.txt). Padrão: agenda.txt global.
        """
        self._path = caminho or AGENDA_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()
            logger.info("Arquivo de agenda criado em %s", self._path)

    def trocar(self, caminho: Path | None = None) -> None:
        """
        Troca o arquivo de agenda em uso (perfis por rosto).

        Quem guarda referência à instância (rotinas, proativo, quiz, agente)
        passa a usar o novo caminho automaticamente. None = volta ao global.
        """
        self._path = caminho or AGENDA_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()
        logger.info("Agenda agora aponta para %s", self._path)

    def cadastrar_evento(self, evento: str) -> None:
        """
        Adiciona um evento à agenda com timestamp.

        Args:
            evento: descrição do evento a ser cadastrado.
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        linha = f"[{timestamp}] {evento}\n"
        with open(self._path, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha)
        logger.info("Evento cadastrado: %s", evento)

    def ler_eventos(self) -> list[str]:
        """
        Lê todos os eventos cadastrados na agenda.

        Returns:
            Lista de eventos (strings), vazia se não houver nenhum.
        """
        with open(self._path, "r", encoding="utf-8") as arquivo:
            eventos = [linha.strip() for linha in arquivo if linha.strip()]
        logger.info("%d evento(s) lido(s) da agenda.", len(eventos))
        return eventos

    def limpar_agenda(self) -> None:
        """Apaga o conteúdo da agenda sem excluir o arquivo."""
        with open(self._path, "w", encoding="utf-8") as arquivo:
            arquivo.write("")
        logger.info("Agenda limpa.")
