"""
Perfis — a câmera vira login.

O face.py já reconhece quem está na frente; este módulo transforma isso
em identidade de sessão:

- `identificar()`: roda o reconhecimento e abre o perfil da pessoa —
  agenda e notas passam a ler/escrever em data/perfis/<nome>/ em vez do
  data/ global (o chico.py troca as instâncias na hora).
- `gate()`: comandos sensíveis (limpar agenda, desligar, bloquear) pedem
  rosto reconhecido primeiro. Se a câmera/OpenCV estiver indisponível,
  o gate não trava o usuário — degrada com aviso no log.
- `sair()`: fecha o perfil e volta aos dados globais.

Segue o padrão dos outros módulos: métodos devolvem a frase a falar.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent
PASTA_PERFIS = RAIZ / "data" / "perfis"

# Respostas do face.reconhecer() que significam "não é uma pessoa conhecida"
_FALHAS_RECONHECIMENTO = (
    "Desconhecido",
    "Nenhum rosto detectado",
    "OpenCV não instalado",
    "Não consegui acessar",
    "Rosto detectado. Cadastre",
)


def _slug(nome: str) -> str:
    """Nome de perfil -> nome de pasta seguro ('Pedro Farath' -> 'pedro_farath')."""
    slug = re.sub(r"[^\w]+", "_", nome.lower()).strip("_")
    return slug or "convidado"


class Perfis:
    """Identidade por rosto: login, troca de usuário e gate biométrico."""

    def __init__(self, face) -> None:
        """Recebe ReconhecimentoFacial (face.py)."""
        self.face = face
        self.usuario_atual: str | None = None

    def _nome_valido(self, nome: str) -> bool:
        """face.reconhecer devolve o nome OU uma frase de falha/desconhecido."""
        return bool(nome) and not any(nome.startswith(f) for f in _FALHAS_RECONHECIMENTO)

    def identificar(self) -> tuple[str, str | None]:
        """
        Reconhece o rosto e abre o perfil correspondente.

        Returns:
            (frase para falar, nome ou None). Com nome, o chico.py troca
            agenda/notas para a pasta do perfil.
        """
        nome = self.face.reconhecer()
        if not self._nome_valido(nome):
            if nome == "Desconhecido":
                return (
                    "Vi um rosto, mas não te conheço. "
                    "Diga 'cadastra meu rosto' para criar seu perfil.",
                    None,
                )
            return (nome, None)  # mensagem de erro do face já é falável
        self.usuario_atual = nome
        logger.info("Perfil aberto: %s", nome)
        return (f"Oi, {nome}! Seu perfil está aberto — agenda e notas agora são só suas.", nome)

    def sair(self) -> str:
        """Fecha o perfil atual e volta aos dados globais."""
        if not self.usuario_atual:
            return "Ninguém está com perfil aberto."
        nome = self.usuario_atual
        self.usuario_atual = None
        logger.info("Perfil fechado: %s", nome)
        return f"Até logo, {nome}. Voltei aos dados globais."

    def quem(self) -> str:
        """Diz quem está logado (sem abrir a câmera de novo)."""
        if self.usuario_atual:
            return f"Perfil aberto: {self.usuario_atual}."
        return "Nenhum perfil aberto. Diga 'me reconhece' para entrar pelo rosto."

    def pasta_perfil(self, nome: str) -> Path:
        """Pasta de dados do perfil — data/perfis/<slug>/."""
        pasta = PASTA_PERFIS / _slug(nome)
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta

    def gate(self) -> str | None:
        """
        Portão biométrico para comandos sensíveis.

        Returns:
            None = autorizado (perfil já aberto, ou rosto reconhecido agora,
            ou câmera indisponível — degrada aberto com aviso no log).
            str  = mensagem de negação a falar (rosto visto mas desconhecido).
        """
        if self.usuario_atual:
            return None
        nome = self.face.reconhecer()
        if self._nome_valido(nome):
            self.usuario_atual = nome
            return None  # chico aplica o perfil e segue com o comando
        if nome == "Desconhecido":
            return "Rosto não reconhecido — esse comando é sensível. Cadastre seu rosto primeiro."
        # Sem câmera/OpenCV: não trava o usuário
        logger.warning("Gate biométrico degradado: %s", nome)
        return None


if __name__ == "__main__":
    # Teste com face fake: fluxo de login/gate/sair sem câmera
    class _FaceFake:
        def __init__(self, resposta):
            self.resposta = resposta
        def reconhecer(self):
            return self.resposta

    p = Perfis(_FaceFake("Pedro"))
    msg, nome = p.identificar()
    assert nome == "Pedro" and p.usuario_atual == "Pedro"
    assert p.gate() is None
    print(msg)
    assert "Nenhum perfil" not in p.quem()

    p2 = Perfis(_FaceFake("Desconhecido"))
    msg, nome = p2.identificar()
    assert nome is None and "Cadastre" in msg or "cadastra" in msg
    assert p2.gate() is not None  # desconhecido: bloqueia
    print(msg)

    p3 = Perfis(_FaceFake("Não consegui acessar a câmera."))
    assert p3.gate() is None  # sem hardware: degrada aberto
    p.usuario_atual = "Pedro"
    print(p.sair())
    print("perfis OK")
