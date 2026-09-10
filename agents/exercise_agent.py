import os
import json
from dotenv import load_dotenv
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
from services.database import SUBJECT_CONFIG
from services.llm_client import execute_generate

load_dotenv()

class ExerciseItem(BaseModel):
    title: str = Field(description="Titre de l'exercice avec son intention didactique.")
    instructions: str = Field(description="Énoncé clair, aéré et guidé au format Markdown avec les mots-clés essentiels.")
    hint: str = Field(description="Indice ou astuce sans donner la solution.")
    solution: str = Field(description="Corrigé modèle détaillé pas-à-pas.")

class ExerciseSet(BaseModel):
    exercises: List[ExerciseItem]

class ExerciseAgent:
    def __init__(self):
        pass

    def generate_exercises(self, course_markdown: str, subject: str, cache_name: str | None = None) -> list[dict]:
        config = SUBJECT_CONFIG.get(subject, next(iter(SUBJECT_CONFIG.values())))
        
        user_prompt = "Génère les exercices sur le cours mémorisé." if cache_name else f"COURS :\n{course_markdown}"

        response = execute_generate(
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=config["exercise_prompt"],
                response_mime_type="application/json",
                response_schema=ExerciseSet,
                temperature=0.7,
            ),
            cached_content=cache_name
        )
        return json.loads(response.text).get("exercises", [])