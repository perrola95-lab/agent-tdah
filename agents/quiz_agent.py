import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from typing import List
from services.llm_client import execute_generate, FAST_MODEL


load_dotenv()

class QuizQuestion(BaseModel):
    question: str = Field(description="Intitulé percutant et direct de la question (niveau 4ème).")
    options: List[str] = Field(description="Exactement 4 propositions de réponse.")
    correct_answer_index: int = Field(description="Index de la bonne réponse (0, 1, 2 ou 3).")
    explanation: str = Field(
        description="Feedback bienveillant et complice (12-14 ans, syntaxe parfaite) expliquant pourquoi c'est la bonne réponse et comment déjouer le piège."
    )

class QuizData(BaseModel):
    questions: List[QuizQuestion]

class QuizAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("La variable d'environnement GEMINI_API_KEY est introuvable.")

    def generate_quiz(self, course_markdown: str, cache_name: str | None = None) -> list[dict]:
        body = "À partir du cours en mémoire, génère le quiz." if cache_name else f"COURS DE RÉFÉRENCE :\n{course_markdown}"

        prompt = f"""Génère un quiz d'ancrage mémoriel complet pour réviser sans stress et consolider tous les points clés.

Consignes de fond et de style :
- Exprime-toi dans le langage actuel des jeunes de 12 à 14 ans (*« masterclass »*, *« bien vu »*), avec une grammaire et une orthographe irréprochables.
- Les questions doivent être courtes, concrètes et sans double consigne.
- Propose exactement 4 options de réponse claires.
- Champ explanation : valide si c'est bon, ou explique la bonne réponse avec une astuce mnémotechnique en cas d'erreur.

{body}"""

        response = execute_generate(
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction="Tu es un grand frère ou coach d'études bienveillant pour un collégien de 4ème avec un TDAH.",
                response_mime_type="application/json",
                response_schema=QuizData,
            ),
            cached_content=cache_name
        )

        data = json.loads(response.text)
        return data.get("questions", [])