"""
Proativo — o Chico fala primeiro.

Thread em background que dispara duas coisas sem o usuário pedir:

- lembretes: agenda.txt guarda linhas "[dd/mm/aaaa HH:MM] <texto>"; se o
  texto mencionar um horário ("prova às 18h", "consulta 14:30"), o Chico
  avisa quando o relógio bate;
- presença: a cada intervalo, um frame da webcam passa pelo detector de
  rostos Haar (o mesmo do face.py). Quando alguém APARECE (ausente ->
  presente), o Chico cumprimenta uma vez — com cooldown para não repetir.

Tudo falha em silêncio: sem câmera ou sem opencv o módulo simplesmente
não detecta presença, e lembretes continuam funcionando.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Intervalo do loop de checagem e janela em que um lembrete "vale"
INTERVALO_SEGUNDOS = 30
JANELA_LEMBRETE_MIN = 2
# Presença: checagem a cada 5 min e cooldown de 45 min entre saudações
INTERVALO_PRESENCA_SEG = 300
COOLDOWN_SAUDACAO_MIN = 45

# "prova às 18h30" | "consulta 14:30" | "reunião as 8h" -> (18,30), (14,30), (8,0)
PADRAO_HORARIO = re.compile(
    r"\b(?:às|as|à|para|pras|das)\s*(\d{1,2})\s*(?:[:h]\s*(\d{2}))?\b"
    r"|\b(\d{1,2}):(\d{2})\b"
    r"|\b(\d{1,2})\s*h\s*(\d{2})?\b"
)


def _extrair_horario(texto: str) -> tuple[int, int] | None:
    """Primeira hora mencionada no texto do evento, ou None."""
    match = PADRAO_HORARIO.search(texto.lower())
    if not match:
        return None
    grupos = [g for g in match.groups() if g is not None]
    try:
        hora = int(grupos[0])
        minuto = int(grupos[1]) if len(grupos) > 1 else 0
    except (ValueError, IndexError):
        return None
    if hora > 23 or minuto > 59:
        return None
    return hora, minuto


class Proativo:
    """Thread de fundo que fala lembretes da agenda e sauda presença."""

    def __init__(self, agenda, falar) -> None:
        """
        Args:
            agenda: módulo Agenda (ler_eventos).
            falar: callable(texto) — o self.falar do Chico.
        """
        self.agenda = agenda
        self.falar = falar
        self._ativo = True
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self._avisados: set[str] = set()        # lembretes já falados
        self._presente = False                  # último estado da câmera
        self._ultima_saudacao: datetime | None = None

    # ------------------------------------------------------------------ #
    #  CONTROLE                                                           #
    # ------------------------------------------------------------------ #

    def iniciar(self) -> None:
        """Sobe a thread daemon (morre junto com o processo)."""
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._loop, name="chico-proativo", daemon=True)
        self._thread.start()
        logger.info("Proativo iniciado (lembretes + presença).")

    def parar(self) -> None:
        """Sinaliza a thread para sair no próximo ciclo."""
        self._parar.set()

    def set_ativo(self, ativo: bool) -> str:
        """Liga/desliga os avisos sem matar a thread."""
        self._ativo = ativo
        estado = "ligado" if ativo else "desligado"
        logger.info("Proativo %s.", estado)
        if ativo:
            return "Modo proativo ligado. Eu aviso quando chegar hora de compromisso e quando te vir por aqui."
        return "Modo proativo desligado. Fico quieto até você pedir de volta."

    # ------------------------------------------------------------------ #
    #  LOOP                                                               #
    # ------------------------------------------------------------------ #

    def _loop(self) -> None:
        """Checa lembretes a cada INTERVALO_SEGUNDOS; presença em ritmo próprio."""
        ultimo_check_presenca = 0.0
        while not self._parar.is_set():
            if self._ativo:
                try:
                    self._checar_lembretes()
                except Exception as exc:
                    logger.warning("Checagem de lembretes falhou: %s", exc)
                agora = time.monotonic()
                if agora - ultimo_check_presenca >= INTERVALO_PRESENCA_SEG:
                    ultimo_check_presenca = agora
                    try:
                        self._checar_presenca()
                    except Exception as exc:
                        logger.warning("Checagem de presença falhou: %s", exc)
            self._parar.wait(INTERVALO_SEGUNDOS)

    # ------------------------------------------------------------------ #
    #  LEMBRETES                                                          #
    # ------------------------------------------------------------------ #

    def _checar_lembretes(self) -> None:
        """Avisa quando o horário escrito no texto do evento chega."""
        agora = datetime.now()
        for linha in self.agenda.ler_eventos():
            # "[dd/mm/aaaa HH:MM] texto" — o horário do evento vem do texto
            texto = linha.split("]", 1)[-1].strip()
            horario = _extrair_horario(texto)
            if horario is None:
                continue
            alvo = agora.replace(hour=horario[0], minute=horario[1], second=0, microsecond=0)
            delta = (alvo - agora).total_seconds()
            chave = f"{agora:%Y-%m-%d}|{horario}|{texto}"
            if chave in self._avisados:
                continue
            # Vale se o horário acabou de passar ou está para chegar na janela
            if -60 <= delta <= JANELA_LEMBRETE_MIN * 60:
                self._avisados.add(chave)
                logger.info("Lembrete disparado: %s", texto)
                self.falar(f"Lembrete! Daqui a pouco: {texto}")

    # ------------------------------------------------------------------ #
    #  PRESENÇA                                                           #
    # ------------------------------------------------------------------ #

    def _tem_rosto_agora(self) -> bool | None:
        """Um frame da webcam -> tem rosto? None = câmera indisponível."""
        try:
            import cv2  # type: ignore
        except ImportError:
            return None
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            camera.release()
            return None
        try:
            for _ in range(3):  # descarta frames de aquecimento
                camera.read()
                time.sleep(0.05)
            ok, frame = camera.read()
            if not ok:
                return None
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cascata = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            rostos = cascata.detectMultiScale(cinza, scaleFactor=1.2, minNeighbors=5)
            return len(rostos) > 0
        finally:
            camera.release()

    def _checar_presenca(self) -> None:
        """Sauda uma vez por transição ausente->presente, com cooldown."""
        tem_rosto = self._tem_rosto_agora()
        if tem_rosto is None:
            return  # sem câmera: não faz nada, não repete
        if tem_rosto and not self._presente:
            agora = datetime.now()
            if (
                self._ultima_saudacao is None
                or agora - self._ultima_saudacao > timedelta(minutes=COOLDOWN_SAUDACAO_MIN)
            ):
                self._ultima_saudacao = agora
                logger.info("Presença detectada — saudando.")
                self.falar("Oi! Te vi chegar. Quer um resumo do dia ou alguma coisa específica?")
        self._presente = tem_rosto


if __name__ == "__main__":
    # Teste sem câmera: só a parte de parse de horário e janela de lembrete
    for texto, espera in [
        ("prova de cálculo às 18h30", (18, 30)),
        ("consulta 14:45", (14, 45)),
        ("reunião as 8h", (8, 0)),
        ("almoço", None),
        ("prova às 25h", None),
        ("trabalho para 10 horas", (10, 0)),
    ]:
        achado = _extrair_horario(texto)
        assert achado == espera, (texto, achado, espera)
        print(texto, "->", achado)

    falas: list[str] = []

    class _AgendaFake:
        def ler_eventos(self):
            agora = datetime.now()
            return [f"[{agora:%d/%m/%Y %H:%M}] prova às {agora:%H}h{agora:%M}"]

    p = Proativo(_AgendaFake(), falas.append)
    p._checar_lembretes()
    assert falas and "Lembrete" in falas[0], falas
    p._checar_lembretes()  # não repete o mesmo lembrete
    assert len(falas) == 1
    print("proativo OK")
