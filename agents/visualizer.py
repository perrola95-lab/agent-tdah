# agents/visualizer.py
import re
import base64
from dotenv import load_dotenv
from google.genai import types
from services.llm_client import execute_generate, FAST_MODEL, get_client

load_dotenv()

class VisualizerAgent:
    def __init__(self):
        self.client = get_client()

    @staticmethod
    def _sanitize(text: str) -> str:
        """Nettoie les caractères interdits dans la syntaxe Mermaid."""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'["\'\(\)\[\]\{\};:#`]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _wrap_title(text: str, max_chars_per_line: int = 26) -> str:
        """Découpe un texte long sur plusieurs lignes sans jamais tronquer les mots."""
        words = text.split()
        if not words:
            return "Cours"
        lines = []
        current_line = []
        current_len = 0

        for w in words:
            if current_len + len(w) > max_chars_per_line and current_line:
                lines.append(" ".join(current_line))
                current_line = [w]
                current_len = len(w)
            else:
                current_line.append(w)
                current_len += len(w) + 1

        if current_line:
            lines.append(" ".join(current_line))

        return "<br/>".join(lines)

    @classmethod
    def inject_playful_styling(cls, raw_mermaid: str) -> str:
        """Injecte automatiquement une palette de styles ultra-colorée et ludique pour chaque branche."""
        if not raw_mermaid or "graph" not in raw_mermaid:
            return raw_mermaid

        # Détecter les branches principales reliées à Root (ex: Root --> A[...] ou Root --> A)
        main_branches = re.findall(r'Root\s*-->\s*([A-Za-z0-9_]+)', raw_mermaid)
        branch_letters = ['A', 'B', 'C', 'D']
        class_assignments = ["    class Root rootStyle;"]

        for idx, b_id in enumerate(main_branches[:4]):
            letter = branch_letters[idx]
            class_assignments.append(f"    class {b_id} branch{letter};")
            
            # Détecter les sous-noeuds de cette branche (ex: A --> A1[...])
            sub_nodes = re.findall(rf'{b_id}\s*-->\s*([A-Za-z0-9_]+)', raw_mermaid)
            if sub_nodes:
                class_assignments.append(f"    class {','.join(sub_nodes)} leaf{letter};")

        styling = """
    classDef rootStyle fill:#FFF3BF,stroke:#FAB005,stroke-width:3.5px,color:#212529,font-weight:bold,rx:18,ry:18;
    classDef branchA fill:#D0EBFF,stroke:#228BE6,stroke-width:2.5px,color:#1864AB,font-weight:bold,rx:14,ry:14;
    classDef branchB fill:#D3F9D8,stroke:#40C057,stroke-width:2.5px,color:#2B8A3E,font-weight:bold,rx:14,ry:14;
    classDef branchC fill:#FFE3E3,stroke:#FA5252,stroke-width:2.5px,color:#C92A2A,font-weight:bold,rx:14,ry:14;
    classDef branchD fill:#F3D9FA,stroke:#BE4BDB,stroke-width:2.5px,color:#862E9C,font-weight:bold,rx:14,ry:14;
    classDef leafA fill:#F8FAFC,stroke:#74C0FC,stroke-width:2px,color:#1971C2,rx:10,ry:10;
    classDef leafB fill:#F8FAFC,stroke:#8CE99A,stroke-width:2px,color:#2F9E44,rx:10,ry:10;
    classDef leafC fill:#F8FAFC,stroke:#FFA8A8,stroke-width:2px,color:#E03131,rx:10,ry:10;
    classDef leafD fill:#F8FAFC,stroke:#EEBEFA,stroke-width:2px,color:#9C36B5,rx:10,ry:10;"""

        assignments_str = "\n".join(class_assignments)
        return f"{raw_mermaid.strip()}\n{styling}\n{assignments_str}\n"

    def generate_mindmap_code(self, course_markdown: str) -> str:
        if not course_markdown:
            return ""

        # 1. Extraction du titre avec emoji sympa
        first_line = course_markdown.strip().split("\n")[0].replace("#", "").strip()
        sanitized_title = self._sanitize(first_line)
        
        # 2. Racine avec découpage et emoji marquant
        has_emoji = bool(re.search(r'[\U00010000-\U0010ffff]', sanitized_title))
        root_prefix = "" if has_emoji else "🧠 "
        formatted_root = root_prefix + self._wrap_title(sanitized_title, max_chars_per_line=24)

        clean_course = re.sub(r"<svg[\s\S]*?</svg>", "", course_markdown)
        clean_course = re.sub(r"<[^>]+>", "", clean_course)

        prompt = f"""EXTRAIT DU COURS :
{clean_course[:2800]}

TITRE DU COURS :
{sanitized_title}

RÔLE : Expert en sketchnote pédagogique et cartes visuelles ludiques pour un élève de 4ème (13 ans) avec TDAH.
OBJECTIF : Générer un diagramme Mermaid 'graph LR' ultra-visuel, expressif, coloré et amusant.

CONSIGNES STRICTES :
1. Débuter obligatoirement par 'graph LR'.
2. La racine DOIT être exactement : Root["{formatted_root}"]
3. Définis 3 (ou 4 max) notions piliers (A, B, C...) débutant CHACUNE par un emoji très expressif et parlant (ex: 🚀, ⚡, 🎯, 🔥, 💎, 🌋, 🍕, 🧪...).
4. Sous chaque notion pilier, ajoute 2 sous-points concrets (A1, A2, B1, B2...) débutant CHACUN par un emoji imagé (ex: 📐, 🔍, 💡, 📏, 🧩, 🏆, ✨, 💥, ⚙️, 🚦...).
5. RÈGLE D'OR TDAH (PUNCHY, CONCRET & AMUSANT) :
   - Chaque libellé doit être COURT et PERCUTANT (2 à 4 mots maximum).
   - Utilise des métaphores ou des expressions amusantes et concrètes (ex: '🍕 Somme 180°', '⚡ Formule Magique', '⚠️ Piège à Éviter', '🏆 Astuce Gagnante').
   - AUCUN terme austère ou jargon abstrait sans image.
   - SANS ponctuation complexe, sans guillemets, sans apostrophe dans les textes (remplace les apostrophes par des espaces).
6. Réponds UNIQUEMENT avec le code Mermaid brut débutant par 'graph LR', sans aucun texte avant ou après, sans bloc markdown.

EXEMPLE ATTENDU :
graph LR
    Root["{formatted_root}"]
    Root --> A["🚀 Théorème Magique"]
    Root --> B["🎯 Propriétés Clés"]
    Root --> C["⚡ Calculs & Astuces"]
    A --> A1["📐 Hypoténuse au Carré"]
    A --> A2["📏 Détecter Angle Droit"]
    B --> B1["🔍 Trois Côtés Égaux"]
    B --> B2["🍕 Somme des Angles 180°"]
    C --> C1["💡 Astuce Racine Carrée"]
    C --> C2["🏆 Formule Gagnante"]
"""

        try:
            response = execute_generate(
                contents=[prompt],
                model=FAST_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction="Générateur de code Mermaid LR strict, ultra-visuel et ludique avec emojis sur chaque noeud. Aucun bloc markdown englobant.",
                    max_output_tokens=600,
                    temperature=0.3
                )
            )

            raw = response.text.strip()
            raw = re.sub(r"^```(?:mermaid)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw).strip()
            raw = raw.replace("'", " ")

            if "graph LR" in raw or "graph TD" in raw:
                return self.inject_playful_styling(raw)

            return ""

        except Exception as err:
            print(f"[VisualizerAgent Exception] : {err}")
            return ""

