import json
from dotenv import load_dotenv
from google.genai import types
from pydantic import BaseModel, Field
from services.llm_client import execute_generate, FAST_MODEL

load_dotenv()

class TutorStepResponse(BaseModel):
    feedback: str = Field(
        description="Feedback direct, bienveillant et complice (style 12-14 ans, orthographe parfaite) sur la réponse précédente. Vide si c'est la première étape."
    )
    next_instruction: str = Field(
        description="Explication ultra-courte de la notion ou de la micro-étape suivante (2-3 phrases max)."
    )
    challenge_question: str = Field(
        description="Micro-question concrète ou petit défi immédiat pour vérifier que l'élève a compris avant de continuer."
    )
    hint: str = Field(
        description="Petit indice si l'élève hésite ou bloque."
    )
    is_completed: bool = Field(
        description="True si toutes les notions clés du cours ont été validées avec succès, False sinon."
    )

class TutorAgent:
    def __init__(self):
        pass

    def guide_step(self, course_markdown: str, history: list[dict], user_reply: str = "", cache_name: str | None = None, subject: str | None = None) -> dict:
        # Fenêtre glissante : 4 derniers échanges max pour limiter la consommation de tokens
        recent_history = history[-4:] if len(history) > 4 else history
        history_formatted = "\n".join([f"{h['role'].upper()} : {h['text']}" for h in recent_history])

        body = "Réfère-toi au cours mis en mémoire." if cache_name else f"COURS DE RÉFÉRENCE :\n{course_markdown[:3000]}"

        prompt = f"""{body}

HISTORIQUE RÉCENT :
{history_formatted}

DERNIÈRE RÉPONSE DE L'ÉLÈVE :
« {user_reply} »"""

        subj_clause = f" dans la discipline : {subject}" if subject else ""
        system_instruction = f"""Tu es un tuteur particulier bienveillant, énergique et ultra-pédagogue pour un collégien de 4ème avec TDAH{subj_clause}.
Règles :
1. Une seule micro-notion à la fois (4-5 étapes max pour tout le cours).
2. Question courte et stimulante (challenge_question).
3. Langage 12-14 ans valorisant, orthographe irréprochable.
4. Passe is_completed à True uniquement à la fin du cours."""

        target_model = FAST_MODEL if not cache_name else "gemini-flash-latest"

        response = execute_generate(
            contents=[prompt],
            model=target_model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=TutorStepResponse,
                max_output_tokens=350,
                temperature=0.3,
            ),
            cached_content=cache_name       
        )
        return json.loads(response.text)