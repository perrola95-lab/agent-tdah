import os
import re
import json
import time
import base64
import io
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError
from services.database import SUBJECT_CONFIG, SYSTEM_INSTRUCTION
from PIL import Image
from services.llm_client import execute_generate, FAST_MODEL


load_dotenv()

def _compress_image_bytes(data_bytes: bytes, max_dim: int = 1024) -> bytes:
    try:
        img = Image.open(io.BytesIO(data_bytes))
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
        # Gestion de la transparence pour la conversion en JPEG
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.convert("RGBA").split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
            
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=80)
        return out.getvalue()
    except Exception:
        return data_bytes
        
class DetectedSubject(BaseModel):
    category: str = Field(
        description="Catégorie exacte de la matière : 'Mathématiques, Physique-Chimie, Technologie', 'Histoire-Géographie, EMC, SVT', ou 'Lettres & Langues'"
    )
    specific_subject: str = Field(
        description="Matière scolaire précise (ex: 'Mathématiques', 'Histoire-Géographie', 'SVT', 'Physique-Chimie', 'Français', 'Anglais', 'Technologie', 'EMC')"
    )
    topic: str = Field(
        description="Thème ou titre du chapitre identifié (ex: 'Théorème de Pythagore', 'La Révolution française', 'La tectonique des plaques')"
    )
    confidence: str = Field(
        description="Niveau de certitude : 'élevé' ou 'moyen'"
    )
    rationale: str = Field(
        description="Justification concise en une phrase expliquant la détection"
    )

class CuratorAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("La variable d'environnement GEMINI_API_KEY est introuvable.")

    def detect_subject(self, uploaded_files_data: list[dict], extra_text: str = "") -> dict:
        """Détecte automatiquement la matière, la catégorie de prompt et le thème à partir des documents."""
        system_instruction = """Tu es un classificateur pédagogique expert du collège français (niveau 4ème).
Ton rôle : analyser les documents fournis pour identifier avec précision la matière scolaire et le thème abordé.

Catégories obligatoires (champ 'category') :
1. "Mathématiques, Physique-Chimie, Technologie" : pour tout ce qui concerne le calcul, la géométrie, l'algèbre, la physique, la chimie, l'électricité, l'informatique/techno.
2. "Histoire-Géographie, EMC, SVT" : pour l'histoire, la géographie, l'éducation morale et civique, et les sciences de la vie et de la Terre (biologie, géologie, corps humain, plaques tectoniques).
3. "Lettres & Langues" : pour le français (grammaire, conjugaison, orthographe, littérature) et les langues vivantes ou anciennes (anglais, espagnol, allemand, latin).

Remplis également la matière spécifique (ex: 'Mathématiques', 'Histoire-Géographie', 'SVT', 'Français'...) et le chapitre/thème identifié."""

        contents = ["Identifie la matière et le thème de ces documents de cours de 4ème :"]

        # Échantillonnage représentatif pour une détection ultra-rapide (<1.5s)
        for item in uploaded_files_data[:3]:
            mime_type = item["mime_type"]
            data_bytes = item["bytes"]

            if mime_type.startswith("text/"):
                sample_txt = data_bytes.decode("utf-8", errors="ignore")[:2500]
                contents.append(f"--- Fichier ({item['name']}) ---\n{sample_txt}")
            elif mime_type.startswith("image/"):
                compressed = _compress_image_bytes(data_bytes, max_dim=800)
                contents.append(types.Part.from_bytes(data=compressed, mime_type="image/jpeg"))
            else:
                contents.append(types.Part.from_bytes(data=data_bytes, mime_type=mime_type))

        if extra_text.strip():
            contents.append(f"Notes / Consignes : {extra_text[:1500]}")

        # Si aucun contenu n'a été fourni
        if len(contents) == 1:
            return {
                "category": "Mathématiques, Physique-Chimie, Technologie",
                "specific_subject": "Mathématiques",
                "topic": "Cours général",
                "confidence": "moyen",
                "rationale": "Aucun document fourni, catégorie par défaut appliquée."
            }

        try:
            response = execute_generate(
                contents=contents,
                model=FAST_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=DetectedSubject,
                    temperature=0.1
                )
            )

            data = json.loads(response.text)
            valid_categories = list(SUBJECT_CONFIG.keys())

            # Sécurisation de la catégorie exacte
            if data.get("category") not in valid_categories:
                cat_lower = (data.get("category") or "").lower()
                if any(k in cat_lower for k in ["math", "physiq", "chimie", "techno", "calcul"]):
                    data["category"] = valid_categories[0]
                elif any(k in cat_lower for k in ["hist", "géo", "geo", "svt", "emc", "terre", "bio"]):
                    data["category"] = valid_categories[1]
                else:
                    data["category"] = valid_categories[2]

            return data

        except Exception as e:
            print(f"[detect_subject exception] : {e}")
            return {
                "category": "Mathématiques, Physique-Chimie, Technologie",
                "specific_subject": "Mathématiques",
                "topic": "Cours",
                "confidence": "moyen",
                "rationale": "Détection automatique de repli."
            }

    @staticmethod
    def _format_markdown_and_svg(text: str) -> str:
        """Nettoie le texte, sécurise le SVG inline et applique la charte graphique."""
        content = text.strip()

        # 1. Nettoyage des blocs Markdown englobants
        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.startswith("```"):
            content = content[len("```"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        # 2. Supprime les backticks isolés autour des SVG (ex: ```xml <svg...>```)
        content = re.sub(r'```(?:xml|svg|html)?\s*(<svg[\s\S]*?</svg>)\s*```', r'\1', content, flags=re.IGNORECASE)

        # Nettoyage et confinement du SVG
        def clean_svg_inline(match):
            svg_code = match.group(0).strip()

            # 1. Namespace XML
            if 'xmlns=' not in svg_code:
                svg_code = re.sub(r'<svg\b', '<svg xmlns="http://www.w3.org/2000/svg"', svg_code, count=1, flags=re.IGNORECASE)

            # 2. Dimensions responsives garanties
            # On retire width/height codés en dur s'il y a un viewBox
            if 'viewBox=' in svg_code:
                svg_code = re.sub(r'<svg\b([^>]*?)\s+(?:width|height)="[^"]*"', r'<svg\1', svg_code, flags=re.IGNORECASE)
                svg_code = re.sub(r'<svg\b', '<svg style="width: 100%; max-width: 680px; height: auto; display: block; margin: 0 auto;"', svg_code, count=1, flags=re.IGNORECASE)

            # 3. Échappement des chevrons dans les textes SVG
            def escape_text_content(text_match):
                prefix, content, suffix = text_match.group(1), text_match.group(2), text_match.group(3)
                safe_content = content.replace("<", "&lt;").replace(">", "&gt;")
                return f"{prefix}{safe_content}{suffix}"

            svg_code = re.sub(r'(<text[^>]*>)(.*?)(</text>)', escape_text_content, svg_code, flags=re.DOTALL | re.IGNORECASE)

            # 4. Bloc conteneur isolé : block complet + clear both + triples sauts de ligne pour forcer un nouveau paragraphe Markdown
            return (
                f'\n\n<div style="display: block; clear: both; width: 100%; text-align: center; margin: 30px 0;">'
                f'{svg_code}'
                f'</div>\n\n<div style="clear: both;"></div>\n\n'
            )

        content = re.sub(r'<svg[\s\S]*?<\/svg>', clean_svg_inline, content, flags=re.IGNORECASE)
        return content


    def process_course(self, uploaded_files_data: list[dict], subject: str, extra_text: str = "", subject_detail: dict | None = None) -> str:
        config = SUBJECT_CONFIG.get(subject, next(iter(SUBJECT_CONFIG.values())))
        task_prompt = config["course_prompt"]

        contents = [task_prompt]

        if subject_detail:
            spec = subject_detail.get("specific_subject", "")
            top = subject_detail.get("topic", "")
            if spec or top:
                contents.append(f"CONTEXTE DE LA DISCIPLINE : Matière exacte = {spec} | Chapitre/Thème = {top}\n")

        for item in uploaded_files_data:
            mime_type = item["mime_type"]
            data_bytes = item["bytes"]

            if mime_type.startswith("text/"):
                contents.append(f"--- Document ({item['name']}) ---\n" + data_bytes.decode("utf-8", errors="ignore"))
            elif mime_type.startswith("image/"):
                compressed = _compress_image_bytes(data_bytes)
                contents.append(types.Part.from_bytes(data=compressed, mime_type="image/jpeg"))
            else:
                contents.append(types.Part.from_bytes(data=data_bytes, mime_type=mime_type))

        if extra_text.strip():
            contents.append(f"CONSIGNES / NOTES SUPPLÉMENTAIRES :\n{extra_text}")

        # Appel avec le system instruction global
        response = execute_generate(
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        return self._format_markdown_and_svg(response.text)
    
    def answer_chat_question(self, current_course: str, user_question: str) -> str:
        """Répond rapidement et directement sans réécrire l'intégralité de la fiche."""
        prompt = f"""Tu es un grand frère et coach d'études bienveillant pour un collégien de 4ème avec TDAH.
Voici le cours actuel :
{current_course[:2500]}

L'élève pose la question suivante :
« {user_question} »

Consignes :
- Réponds en 3-4 phrases maximum, de façon ultra-claire et concrète.
- Ton complice de 12-14 ans, valorisant et direct, français impeccable."""

        response = execute_generate(
            contents=[prompt],
            model=FAST_MODEL,
            config=types.GenerateContentConfig(
                max_output_tokens=220,
                temperature=0.5
            )
        )
        return response.text.strip()
    
