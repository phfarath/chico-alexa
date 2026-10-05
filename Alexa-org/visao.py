"""
Visão — o Chico ganha olhos.

- ver_tela: print da tela -> Gemini descreve o que está no monitor.
- descrever_cena: foto da webcam -> Gemini descreve o ambiente à frente.

Reutiliza extras.capturar_tela (cadeia mss -> pyautogui -> PIL) e o cliente
Gemini de ia_generativa (google-genai aceita imagem inline).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPT_TELA = (
    "Descreva objetivamente o que aparece nesta captura de tela: "
    "aplicativos abertos, conteúdo principal e qualquer erro visível. "
    "Responda em até 3 frases."
)
PROMPT_CENA = (
    "Descreva objetivamente a cena à frente da câmera: pessoas, "
    "objetos e ambiente. Responda em até 3 frases."
)


class Visao:
    """Captura imagem (tela ou webcam) e descreve com o Gemini multimodal."""

    def __init__(self, extras, ia) -> None:
        """Recebe Extras (captura de tela) e IAGenerativa (cliente Gemini)."""
        self.extras = extras
        self.ia = ia

    def ver_tela(self) -> str:
        """
        Tira print da tela e pergunta ao Gemini o que está nela.

        Returns:
            Descrição falada da tela, ou mensagem de erro.
        """
        caminho = self.extras.capturar_tela()
        if not caminho:
            return "Não consegui capturar a tela. Instale mss: pip install mss"
        try:
            imagem = Path(caminho).read_bytes()
        except OSError as exc:
            logger.error("Falha ao ler screenshot %s: %s", caminho, exc)
            return "Capturei a tela mas não consegui ler o arquivo."
        return self.ia.perguntar_com_imagem(PROMPT_TELA, imagem)

    def descrever_cena(self) -> str:
        """
        Tira uma foto pela webcam e pergunta ao Gemini o que ela mostra.

        Returns:
            Descrição falada da cena, ou mensagem de erro.
        """
        try:
            import cv2  # type: ignore
        except ImportError:
            return "Para descrever a cena preciso do OpenCV: pip install opencv-python"

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            camera.release()
            return "Não consegui abrir a câmera. Verifique a permissão do sistema."
        try:
            # Descarta os primeiros frames: a câmera precisa de instantes
            # para ajustar exposição e não devolver foto escura/tremida
            for _ in range(5):
                camera.read()
                time.sleep(0.05)
            ok, frame = camera.read()
            if not ok:
                return "A câmera abriu mas não veio imagem. Tente de novo."
            sucesso, png = cv2.imencode(".png", frame)
            if not sucesso:
                return "Não consegui codificar a foto da câmera."
            return self.ia.perguntar_com_imagem(PROMPT_CENA, png.tobytes())
        finally:
            camera.release()


if __name__ == "__main__":
    # Teste sem hardware: IA fake confirma que o fluxo chama o método certo
    class _FakeIA:
        def perguntar_com_imagem(self, prompt, imagem, mime_type="image/png"):
            return f"[ia recebeu {len(imagem)} bytes: {prompt[:40]}...]"

    class _FakeExtras:
        def capturar_tela(self):
            return ""

    v = Visao(_FakeExtras(), _FakeIA())
    print(v.ver_tela())
