"""
Módulo de integração com IA Generativa (Google Gemini).
Utiliza a API gratuita do Gemini para responder perguntas abertas.
"""

import logging
import os

from google import genai as google_genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Você é Chico, um assistente virtual inteligente e simpático. "
    "Responda de forma clara e concisa em português brasileiro. "
    "Seja direta e evite respostas muito longas."
)


class IAGenerativa:
    """Integração com o Google Gemini para respostas inteligentes."""

    def __init__(self) -> None:
        """Configura a API do Gemini."""
        self._disponivel = False
        self._client = None
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.warning(
                "GEMINI_API_KEY não configurada. "
                "Defina a variável de ambiente para ativar a IA."
            )
            return
        try:
            self._client = google_genai.Client(api_key=api_key)
            self._disponivel = True
            logger.info("Gemini configurado com sucesso.")
        except Exception as exc:
            logger.error("Erro ao configurar Gemini: %s", exc)

    def perguntar(self, pergunta: str) -> str:
        """
        Envia uma pergunta ao Gemini e retorna a resposta.

        Args:
            pergunta: texto da pergunta do usuário.

        Returns:
            Resposta gerada pela IA, ou mensagem de fallback.
        """
        if not self._disponivel or self._client is None:
            return (
                "A IA generativa não está configurada. "
                "Adicione sua GEMINI_API_KEY no arquivo .env."
            )
        try:
            resposta = self._client.models.generate_content(
                model="gemini-3.5-flash",
                contents=pergunta,
                config=google_genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            texto = (resposta.text or "").strip()
            if not texto:
                return "Não consegui obter uma resposta da IA agora. Tente novamente."
            if len(texto) > 500:
                texto = texto[:500] + "..."
            logger.info("Resposta Gemini obtida (%d chars).", len(texto))
            return texto
        except Exception as exc:
            logger.error("Erro ao consultar Gemini: %s", exc)
            return "Não consegui obter uma resposta da IA agora. Tente novamente."

    def perguntar_com_imagem(self, pergunta: str, imagem: bytes, mime_type: str = "image/png") -> str:
        """
        Envia uma pergunta junto com uma imagem ao Gemini (visão multimodal).

        Args:
            pergunta: instrução sobre a imagem (ex.: "descreva a cena").
            imagem: bytes da imagem (PNG/JPEG).
            mime_type: tipo MIME da imagem.

        Returns:
            Descrição gerada pela IA, ou mensagem de fallback.
        """
        if not self._disponivel or self._client is None:
            return (
                "A IA generativa não está configurada. "
                "Adicione sua GEMINI_API_KEY no arquivo .env."
            )
        try:
            parte_imagem = google_genai.types.Part.from_bytes(
                data=imagem, mime_type=mime_type
            )
            resposta = self._client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[pergunta, parte_imagem],
                config=google_genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            texto = (resposta.text or "").strip()
            if not texto:
                return "Não consegui analisar a imagem agora. Tente novamente."
            if len(texto) > 500:
                texto = texto[:500] + "..."
            logger.info("Resposta Gemini (imagem) obtida (%d chars).", len(texto))
            return texto
        except Exception as exc:
            logger.error("Erro ao enviar imagem ao Gemini: %s", exc)
            return "Não consegui analisar a imagem agora. Tente novamente."
