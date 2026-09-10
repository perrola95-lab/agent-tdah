import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY introuvable.")
        _client = genai.Client(api_key=api_key)
    return _client

# Modèles disponibles
DEFAULT_MODEL = "gemini-flash-latest"
FAST_MODEL = "gemini-flash-lite-latest"

MODELS_CASCADE = [
    DEFAULT_MODEL,
    FAST_MODEL,
    "gemini-pro-latest"
]

PRIMARY_MODEL = DEFAULT_MODEL
MIN_CACHE_TOKENS = 2048

def create_course_cache(course_markdown: str, ttl_minutes: int = 45) -> str | None:
    """Crée un cache de contexte si le cours atteint le seuil minimum de tokens."""
    client = get_client()
    try:
        count_res = client.models.count_tokens(
            model=PRIMARY_MODEL,
            contents=[course_markdown]
        )
        if count_res.total_tokens < MIN_CACHE_TOKENS:
            print(f"[llm_client] Cours de {count_res.total_tokens} tokens (< seuil {MIN_CACHE_TOKENS}) : exécution directe sans cache distant.")
            return None

        cache = client.cached_contents.create(
            model=PRIMARY_MODEL,
            config=types.CreateCachedContentConfig(
                contents=[course_markdown],
                ttl=f"{ttl_minutes * 60}s",
                display_name="course_cache"
            )
        )
        print(f"[llm_client] Cache distant créé ({count_res.total_tokens} tokens, TTL={ttl_minutes}m) : {cache.name}")
        return cache.name
    except Exception as e:
        print(f"[llm_client] Impossible de créer le cache distant ({e}) : fallback vers exécution directe.")
        return None

def delete_course_cache(cache_name: str | None):
    """Supprime le cache distant Gemini pour libérer la mémoire."""
    if not cache_name:
        return
    client = get_client()
    try:
        client.cached_contents.delete(name=cache_name)
        print(f"[llm_client] Cache distant supprimé : {cache_name}")
    except Exception as e:
        print(f"[llm_client] Erreur suppression cache ({cache_name}) : {e}")

def execute_generate(contents, config=None, model: str = DEFAULT_MODEL, cached_content: str | None = None, max_retries: int = 1):
    """Exécute l'appel sur le modèle demandé, puis bascule en cascade si quota 429."""
    client = get_client()
    last_error = None

    if config is None:
        config = types.GenerateContentConfig()

    # Place le modèle cible en tête de la cascade
    cascade = [model] + [m for m in MODELS_CASCADE if m != model]

    for model_name in cascade:
        current_config = config
        
        # Le cache distant n'est accepté que sur le modèle exact d'origine
        if cached_content and model_name == PRIMARY_MODEL:
            current_config.cached_content = cached_content
        elif hasattr(current_config, 'cached_content'):
            current_config.cached_content = None

        for attempt in range(1, max_retries + 1):
            try:
                return client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=current_config
                )
            except APIError as e:
                last_error = e
                if e.code == 429:
                    break
                elif e.code == 503 and attempt < max_retries:
                    time.sleep(1.5)
                else:
                    break
            except Exception as e:
                last_error = e
                break

    raise RuntimeError(f"Tous les modèles disponibles ont échoué : {last_error}")