import streamlit as st
import streamlit.components.v1 as components
import time
import base64
import markdown
import re

from dotenv import load_dotenv

load_dotenv()

# Prise en charge des Secrets Streamlit Community Cloud
try:
    if hasattr(st, "secrets"):
        for _k, _v in st.secrets.items():
            if isinstance(_v, str) and _k not in os.environ:
                os.environ[_k] = _v
except Exception:
    pass

from agents.curator import CuratorAgent
from agents.visualizer import VisualizerAgent
from agents.quiz_agent import QuizAgent
from agents.exercise_agent import ExerciseAgent
from agents.tutor_agent import TutorAgent
from services.gdocs_service import GDocsService
from services.database import SUBJECTS
from services.llm_client import create_course_cache
from services.llm_client import delete_course_cache
from utils.theme import apply_theme, render_hero_banner
from utils.focus_timer import render_focus_timer
from utils.reading_tools import render_accessibility_toolbar, get_reading_styles, apply_bionic_reading_to_html
from utils.progress_tracker import render_progress_banner, render_learning_missions, render_badges_shelf
from utils.auth_ui import render_auth_page
from utils.admin_ui import render_admin_panel

st.set_page_config(page_title="Coach d'Apprentissage TDAH (4ème)", page_icon="🧠", layout="wide")

if 'uploader_version' not in st.session_state:
    st.session_state['uploader_version'] = 0

version = st.session_state['uploader_version']

apply_theme()

# --- PORTIER DE SÉCURITÉ & AUTHENTIFICATION ---
if not st.session_state.get("authenticated", False):
    render_auth_page()
    st.stop()

current_user = st.session_state.get("user", {})

col_hero, col_user_actions = st.columns([3.8, 1.8], vertical_alignment="top")
with col_hero:
    render_hero_banner()
with col_user_actions:
    st.write("")
    user_name = current_user.get("name", "Élève")
    user_email = current_user.get("email", "")
    is_admin = current_user.get("is_admin", False)
    plan_tag = "👑 Admin" if is_admin else f"⭐ {current_user.get('subscription_plan', 'Gratuit').capitalize()}"
    
    st.markdown(
        f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 8px 12px; margin-bottom: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
            <div style="font-weight: 800; font-size: 0.88rem; color: #1e1b4b;">👤 {user_name}</div>
            <div style="font-size: 0.75rem; color: #64748b;">{user_email} • <span style="color: #4f46e5; font-weight: 700;">{plan_tag}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("🚪 Déconnexion", type="secondary", use_container_width=True, help="Fermer votre session sécurisée"):
        st.session_state.clear()
        st.rerun()

# Panneau d'administration si l'utilisateur est admin
if current_user.get("is_admin", False):
    render_admin_panel()

# Bandeau de progression & Sprint Focus Timer
col_banner_prog, col_banner_timer = st.columns([3.2, 2.2], vertical_alignment="top")
with col_banner_prog:
    render_progress_banner()
with col_banner_timer:
    render_focus_timer()
    if st.button("🗑️ Vider fiche", type="secondary", use_container_width=True, help="Efface la leçon en cours et remet l'application à zéro"):
        # 1. Suppression du cache distant Gemini s'il existe
        cached_name = st.session_state.get('course_cache_name')
        if cached_name:
            delete_course_cache(cached_name)

        # 2. Vider les caches Streamlit
        st.cache_data.clear()
        st.cache_resource.clear()

        # 3. Conserver la session utilisateur mais purger les données de cours
        saved_auth = st.session_state.get("authenticated", False)
        saved_user = st.session_state.get("user", {})
        next_version = st.session_state.get('uploader_version', 0) + 1

        st.session_state.clear()
        st.session_state["authenticated"] = saved_auth
        st.session_state["user"] = saved_user
        st.session_state['uploader_version'] = next_version
        st.rerun()

        
tabs = st.tabs([
    "📚 Ingestion & Génération", 
    "🎯 Apprentissage Guidé",
    "✍️ Exercices d'Entraînement", 
    "❓ Quiz & Rappel Actif"
])

# TAB 1 : GENERATION DU COURS
with tabs[0]:
    st.header("1. Ingestion des documents de travail")
    
    AUTO_DETECT_OPTION = "🤖 Détection automatique (recommandé)"
    SUBJECT_OPTIONS = [AUTO_DETECT_OPTION] + SUBJECTS

    selected_subject = st.selectbox(
        "🎯 Matière scolaire :",
        options=SUBJECT_OPTIONS,
        key=f"subject_selector_{version}",
        help="L'IA identifie d'elle-même la matière et le thème à partir de tes documents, ou tu peux la choisir manuellement."
    )
    
    st.write("Ajoutez vos documents locaux ou vos fichiers Google Drive (cours, photos, exercices corrigés, PDF, Docs).")

    if 'accumulated_files' not in st.session_state:
        st.session_state['accumulated_files'] = {}

    col_local, col_gdrive = st.columns(2)

    # --- 1. SÉLECTION LOCALE ---
    with col_local:
        st.subheader("💻 Fichiers locaux")
        
        new_files = st.file_uploader(
            "Parcourir vos dossiers locaux :",
            type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "md"],
            accept_multiple_files=True,
            key=f"local_file_selector_{version}"  # <-- Clé dynamique
        )

        if new_files:
            for f in new_files:
                if f.name not in st.session_state['accumulated_files']:
                    st.session_state['accumulated_files'][f.name] = {
                        "name": f.name,
                        "mime_type": f.type if f.type else "application/octet-stream",
                        "bytes": f.getvalue()
                    }

    # --- 2. SÉLECTION GOOGLE DRIVE ---
    with col_gdrive:
        st.subheader("☁️ Fichiers Google Drive")
        
        drive_input = st.text_input(
           "Collez le lien de partage ou l'ID du fichier Drive :",
            key=f"drive_input_{version}"          # <-- Clé dynamique
        )
        
        if st.button("➕ Ajouter le fichier Drive"):
            if drive_input.strip():
                with st.spinner("Téléchargement du fichier depuis Google Drive..."):
                    try:
                        gdocs = GDocsService()
                        drive_file_data = gdocs.fetch_drive_file(drive_input)
                        st.session_state['accumulated_files'][drive_file_data["name"]] = drive_file_data
                        st.success(f"Ajouté : {drive_file_data['name']}")
                    except Exception as e:
                        st.error(f"Erreur Drive : {e}")
            else:
                st.warning("Veuillez renseigner un lien ou un ID valide.")

    # --- GESTION DES DOCUMENTS IMPORTÉS ---
    if st.session_state.get('accumulated_files'):
        col_info, col_clear = st.columns([3, 1], vertical_alignment="center")
        with col_info:
            count = len(st.session_state['accumulated_files'])
            st.caption(f"📁 **{count} document(s) importé(s)** prêt(s) pour l'analyse.")
        with col_clear:
            if st.button("🗑️ Vider les documents importés", key=f"clear_docs_{version}", use_container_width=True):
                st.session_state['accumulated_files'] = {}
                st.session_state['uploader_version'] = st.session_state.get('uploader_version', 0) + 1
                st.rerun()

    extra_notes = st.text_area(
        "Notes ou consignes complémentaires (optionnel) :",
        height=80,
        key=f"extra_notes_{version}"          # <-- Clé dynamique
    )

    # --- BOUTON DE STRUCTURATION ---

    if st.button("🚀 Structurer le cours avec l'IA", type="primary", use_container_width=True):
        # 1. Purge propre de l'ancien cache Gemini s'il existe
        old_cache = st.session_state.get('course_cache_name')
        if old_cache:
            delete_course_cache(old_cache)
            st.session_state.pop('course_cache_name', None)

        # 2. Réinitialisation des états associés au précédent cours
        for key in [
            'mermaid_code', 'course_markdown', 'doc_url',
            'tutor_history', 'tutor_step_data', 'tutor_completed',
            'exercises_list', 'show_solutions',
            'quiz_data', 'quiz_submitted', 'user_quiz_answers',
            'course_chat_history'
        ]:
            st.session_state.pop(key, None)

        if not st.session_state['accumulated_files'] and not extra_notes.strip():
            st.warning("Veuillez ajouter au moins un document ou une note.")
        else:
            curator = CuratorAgent()
            files_payload = list(st.session_state['accumulated_files'].values())

            target_category = selected_subject
            subject_detail = None

            # Détection automatique de la matière si l'option est sélectionnée
            if selected_subject == AUTO_DETECT_OPTION:
                with st.spinner("🔍 Détection intelligente de la matière et du thème..."):
                    subject_detail = curator.detect_subject(
                        uploaded_files_data=files_payload,
                        extra_text=extra_notes
                    )
                    target_category = subject_detail["category"]
                    st.session_state['detected_subject_detail'] = subject_detail
            else:
                st.session_state.pop('detected_subject_detail', None)

            disp_subject = subject_detail.get('specific_subject', target_category) if subject_detail else target_category
            with st.spinner(f"Création de la fiche adaptée TDAH ({disp_subject})..."):
                course_md = curator.process_course(
                    uploaded_files_data=files_payload,
                    subject=target_category,
                    extra_text=extra_notes,
                    subject_detail=subject_detail
                )

                if course_md:
                    st.session_state['course_subject'] = target_category
                    # Création du cache Gemini pour tous les modules suivants
                    cache_name = create_course_cache(course_md, ttl_minutes=45)
                    st.session_state['course_cache_name'] = cache_name
                else:
                    st.error("Impossible de générer le contenu du cours. Vérifiez la réponse de l'API.")
                    st.stop()

                st.session_state['course_markdown'] = course_md

            with st.spinner("Génération de la carte mentale visuelle..."):
                try:
                    visualizer = VisualizerAgent()
                    st.session_state['mermaid_code'] = visualizer.generate_mindmap_code(course_md)
                except Exception as e:
                    print(f"[Visualizer Exception] : {e}")
                
            st.rerun()

# --- RENDU ET EXPORT ---
    if 'course_markdown' in st.session_state:
        st.divider()

        col_badge_t1, col_badge_subj = st.columns([1.6, 2.4], vertical_alignment="center")
        with col_badge_t1:
            st.markdown(
                """
                <div style="display:inline-flex; align-items:center; gap:8px; background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:12px;">
                    <span>⏱️</span> Fiche synthétique : ~3 à 4 min de lecture active
                </div>
                """, 
                unsafe_allow_html=True
            )
        with col_badge_subj:
            det = st.session_state.get('detected_subject_detail')
            if det:
                spec = det.get('specific_subject', 'Matière identifiée')
                top = det.get('topic', '')
                top_badge = f" • {top}" if top else ""
                st.markdown(
                    f"""
                    <div style="display:inline-flex; align-items:center; gap:8px; background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:12px;">
                        <span>🎯</span> Matière détectée : <b>{spec}</b>{top_badge}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif st.session_state.get('course_subject'):
                c_subj = st.session_state.get('course_subject')
                st.markdown(
                    f"""
                    <div style="display:inline-flex; align-items:center; gap:8px; background:#f8fafc; border:1px solid #e2e8f0; color:#475569; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:12px;">
                        <span>🎯</span> Matière : <b>{c_subj}</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # 1. Barre d'outils d'accessibilité (Taille police, Bionic Reading, Police Dyslexie)
        render_accessibility_toolbar()
        st.write("")

        # 2. Missions du jour interactives
        render_learning_missions()
        st.write("")
        
        clean_md = re.sub(
            r':red\[(.*?)\]',
            r'<span style="color: #e63946; font-weight: bold;">\1</span>',
            st.session_state['course_markdown']
        )
        
        clean_md = re.sub(
            r':green\[(.*?)\]',
            r'<span style="color: #2a9d8f; font-weight: bold;">\1</span>',
            clean_md
        )
        
        rendered_html = markdown.markdown(
            clean_md,
            extensions=['extra', 'nl2br', 'sane_lists']
        )

        # Application des styles de lecture adaptés
        reading_styles = get_reading_styles(
            font_size_mode=st.session_state.get('reading_font_size', 'normal'),
            is_dys_mode=st.session_state.get('is_dys_mode', False)
        )
        st.markdown(reading_styles, unsafe_allow_html=True)

        # Application du Bionic Reading si activé
        if st.session_state.get('is_bionic_mode', False):
            rendered_html = apply_bionic_reading_to_html(rendered_html)

        st.markdown(f'<div class="course-reading-container">{rendered_html}</div>', unsafe_allow_html=True)

        # --- CARTE MENTALE VISUELLE (MERMAID) ---
        if st.session_state.get('mermaid_code'):
            st.divider()
            col_mm_title, col_mm_regen = st.columns([3, 1])
            with col_mm_title:
                st.subheader("🎨 Carte Mentale Colorée & Ludique")
                st.caption("Une synthèse ultra-visuelle avec des emojis pour mémoriser les notions clés en un clin d'œil !")
            with col_mm_regen:
                if st.button("🔄 Varier la carte mentale", key="btn_regen_mindmap", use_container_width=True, help="Relance l'IA pour obtenir de nouvelles analogies et emojis amusants !"):
                    with st.spinner("Création d'une nouvelle carte mentale colorée..."):
                        visualizer = VisualizerAgent()
                        st.session_state['mermaid_code'] = visualizer.generate_mindmap_code(st.session_state['course_markdown'])
                        st.rerun()

            m_code = st.session_state['mermaid_code']
            html_mermaid = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    mermaid.initialize({{ 
                        startOnLoad: true,
                        theme: 'base',
                        themeVariables: {{
                            lineColor: '#64748b',
                            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                            fontSize: '15px'
                        }}
                    }});
                </script>
                <style>
                    body {{ 
                        margin: 0; 
                        padding: 10px; 
                        background: transparent; 
                        display: flex; 
                        justify-content: center; 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    }}
                    .mermaid {{
                        background: #ffffff;
                        padding: 24px;
                        border-radius: 16px;
                        border: 2px solid #e2e8f0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                        width: 100%;
                        max-width: 980px;
                        overflow-x: auto;
                    }}
                </style>
            </head>
            <body>
                <div class="mermaid">
{m_code}
                </div>
            </body>
            </html>
            """
            components.html(html_mermaid, height=540, scrolling=True)
        elif 'course_markdown' in st.session_state:
            if st.button("🎨 Générer la carte mentale colorée"):
                with st.spinner("Génération de la carte mentale..."):
                    visualizer = VisualizerAgent()
                    st.session_state['mermaid_code'] = visualizer.generate_mindmap_code(st.session_state['course_markdown'])
                    st.rerun()

    # --- ESPACE CHAT / AJUSTEMENT DU COURS --- 
    if 'course_markdown' in st.session_state:
        st.divider()
        st.subheader("💬 Un doute ? Une question sur ce cours ?")
        st.caption("Pose ta question si un point n'est pas clair : le coach te répond directement !")

        if "course_chat_history" not in st.session_state:
            st.session_state["course_chat_history"] = []

        for msg in st.session_state["course_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)

        user_query = st.chat_input("Ex: Je n'ai pas compris la différence entre troncature et arrondi...")

        if user_query:
            st.session_state["course_chat_history"].append({"role": "user", "content": user_query})
            
            with st.spinner("Le coach te répond..."):
                curator = CuratorAgent()
                reply = curator.answer_chat_question(
                    current_course=st.session_state['course_markdown'],
                    user_question=user_query
                )

                st.session_state["course_chat_history"].append({"role": "assistant", "content": reply})
                st.rerun()
                    
        st.divider()
        st.subheader("💾 Sauvegarde & Export de la fiche")
        st.caption("Choisis ton format d'export préféré : Google Docs connecté ou téléchargement local direct.")

        first_line = st.session_state['course_markdown'].strip().split("\n")[0].replace("#", "").strip()
        doc_title = first_line if first_line else "Fiche de Révision 4ème"
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-]', '_', doc_title).strip('_') or "fiche_revision_4eme"

        # Template HTML autonome avec styling adapté, impression PDF et intégration des schémas SVG & Mermaid
        mermaid_html_block = ""
        mermaid_script = ""
        if st.session_state.get('mermaid_code'):
            m_code = st.session_state['mermaid_code']
            mermaid_html_block = f"""
    <div style="margin-top: 40px; page-break-inside: avoid;">
        <h2 style="color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">🎨 Carte Mentale Colorée & Ludique</h2>
        <div class="mermaid" style="background:#ffffff; padding:24px; border-radius:16px; border:2px solid #e2e8f0; margin-top:16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
{m_code}
        </div>
    </div>
"""
            mermaid_script = """
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'base',
            themeVariables: {
                lineColor: '#64748b',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                fontSize: '15px'
            }
        });
    </script>
"""

        standalone_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>{doc_title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 860px;
            margin: 40px auto;
            padding: 0 24px;
            line-height: 1.6;
            color: #1e293b;
            background-color: #ffffff;
        }}
        h1 {{ color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 24px; }}
        h2 {{ color: #2563eb; margin-top: 32px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }}
        h3 {{ color: #3b82f6; margin-top: 20px; }}
        blockquote {{
            border-left: 4px solid #6366f1;
            padding: 10px 18px;
            margin: 18px 0;
            background-color: #f8fafc;
            border-radius: 0 8px 8px 0;
        }}
        svg {{ max-width: 100%; height: auto; }}
        @media print {{
            body {{ max-width: 100%; margin: 0; padding: 15mm; }}
            h1 {{ font-size: 20pt; }}
            h2 {{ font-size: 16pt; }}
        }}
    </style>
{mermaid_script}
</head>
<body>
{rendered_html}
{mermaid_html_block}
</body>
</html>"""

        col_gdoc, col_html, col_md = st.columns([1.4, 1.3, 1.3])

        with col_gdoc:
            if st.button("📄 Créer le Google Doc", use_container_width=True, type="primary"):
                with st.spinner("Exportation vers Google Docs..."):
                    try:
                        gdocs = GDocsService()
                        doc_url = gdocs.create_adapted_doc(
                            course_markdown=st.session_state['course_markdown'],
                            title=doc_title,
                            mermaid_code=st.session_state.get('mermaid_code')
                        )
                        st.session_state['doc_url'] = doc_url
                    except Exception as e:
                        st.session_state['doc_url'] = None
                        st.error(f"Erreur : {e}")

        with col_html:
            st.download_button(
                label="🌐 Télécharger (HTML / PDF)",
                data=standalone_html,
                file_name=f"{safe_filename}.html",
                mime="text/html",
                use_container_width=True,
                help="Fiche prête à être ouverte dans votre navigateur ou imprimée en PDF !"
            )

        export_md = st.session_state['course_markdown']
        if st.session_state.get('mermaid_code'):
            export_md += f"\n\n## 🗺️ Carte Mentale Visuelle\n\n```mermaid\n{st.session_state['mermaid_code']}\n```\n"

        with col_md:
            st.download_button(
                label="📥 Télécharger (Markdown)",
                data=export_md,
                file_name=f"{safe_filename}.md",
                mime="text/markdown",
                use_container_width=True,
                help="Fichier source Markdown avec carte mentale"
            )

        if st.session_state.get('doc_url'):
            st.success(f"✅ Document prêt : [Ouvrir dans Google Docs]({st.session_state['doc_url']})")

        # Étagère de trophées & badges
        render_badges_shelf()

# TAB 2 : APPRENTISSAGE GUIDÉ PAS-À-PAS
with tabs[1]:
    st.header("🎯 Parcours d'Apprentissage Guidé")
    st.caption("On avance étape par étape ensemble : une notion, une petite question, zéro stress !")

    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:14px;">
            <span>⏱️</span> Défi interactif : ~5 min • 3 à 4 micro-étapes pas-à-pas
        </div>
        """, 
        unsafe_allow_html=True
    )

    if 'course_markdown' not in st.session_state:
        st.info("Veuillez d'abord générer un cours dans le premier onglet pour lancer l'apprentissage guidé.")
    else:
        if 'tutor_history' not in st.session_state:
            st.session_state['tutor_history'] = []
            st.session_state['tutor_step_data'] = None
            st.session_state['tutor_completed'] = False

        col_start, col_reset = st.columns([2, 1])
        with col_start:
            if not st.session_state['tutor_history']:
                if st.button("🚀 Démarrer l'apprentissage guidé", key="btn_start_tutor", type="primary"):
                    with st.spinner("Ton coach prépare la première étape..."):
                        tutor = TutorAgent()
                        step_data = tutor.guide_step(
                            course_markdown=st.session_state['course_markdown'],
                            history=[],
                            cache_name=st.session_state.get('course_cache_name'),
                            subject=st.session_state.get('course_subject')
                        )
                        st.session_state['tutor_step_data'] = step_data
                        st.session_state['tutor_history'].append({
                            "role": "tutor",
                            "text": f"{step_data['next_instruction']}\n\n**Défi :** {step_data['challenge_question']}"
                        })
                        st.rerun()

        with col_reset:
            if st.session_state['tutor_history']:
                if st.button("🔄 Recommencer le parcours", key="btn_reset_tutor"):
                    st.session_state['tutor_history'] = []
                    st.session_state['tutor_step_data'] = None
                    st.session_state['tutor_completed'] = False
                    st.rerun()

        # Affichage du fil de discussion guidé
        for msg in st.session_state['tutor_history']:
            with st.chat_message("assistant" if msg["role"] == "tutor" else "user"):
                st.markdown(msg["text"])

        # Interface de saisie si le parcours est en cours
        if st.session_state.get('tutor_step_data') and not st.session_state.get('tutor_completed', False):
            current_step = st.session_state['tutor_step_data']

            # Indice rétractable
            if current_step.get("hint"):
                with st.expander("💡 Besoin d'un coup de pouce ?"):
                    st.info(current_step["hint"])

            student_answer = st.chat_input("Ta réponse au défi ci-dessus...")

            if student_answer:
                # 1. Enregistrement de la réponse de l'élève
                st.session_state['tutor_history'].append({
                    "role": "student",
                    "text": student_answer
                })

                # 2. Appel du tuteur pour l'étape suivante
                with st.spinner("Le coach regarde ta réponse..."):
                    tutor = TutorAgent()
                    next_step = tutor.guide_step(
                        course_markdown=st.session_state['course_markdown'],
                        history=st.session_state['tutor_history'],
                        user_reply=student_answer,
                        cache_name=st.session_state.get('course_cache_name'),
                        subject=st.session_state.get('course_subject')
                    )                   
                    
                    st.session_state['tutor_step_data'] = next_step

                    # Construction du message retour
                    reply_text = f"**{next_step['feedback']}**\n\n"
                    if not next_step.get('is_completed', False):
                        reply_text += f"{next_step['next_instruction']}\n\n**Défi :** {next_step['challenge_question']}"
                    else:
                        reply_text += "🎉 **Masterclass totale ! Tu as validé toutes les notions clés de ce cours.** Tu peux maintenant t'entraîner sur les exercices ou tester le quiz !"
                        st.session_state['tutor_completed'] = True

                    st.session_state['tutor_history'].append({
                        "role": "tutor",
                        "text": reply_text
                    })
                    st.rerun()

        if st.session_state.get('tutor_completed', False):
            st.balloons()
            st.success("🏆 Parcours guidé terminé avec succès !")
            
# TAB 3 : EXERCICES D'ENTRAÎNEMENT
with tabs[2]:
    st.header("✍️ Exercices d'Application & Corrigés")
    st.caption("Entraîne-toi avec des indices progressifs pour consolider ta mémoire !")

    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:14px;">
            <span>⏱️</span> Entraînement : ~8 min • 3 exercices à difficulté progressive
        </div>
        """, 
        unsafe_allow_html=True
    )

    if 'course_markdown' not in st.session_state:
        st.info("Veuillez d'abord générer un cours dans le premier onglet.")
    else:
        if st.button("📝 Générer les exercices d'entraînement", type="primary"):
            with st.spinner("Création des exercices adaptés au cours..."):
                try:
                    ex_agent = ExerciseAgent()
                    subject_for_exercises = st.session_state.get('course_subject', SUBJECTS[0])
                    st.session_state['exercises_list'] = ex_agent.generate_exercises(
                        course_markdown=st.session_state['course_markdown'],
                        subject=subject_for_exercises,
                        cache_name=st.session_state.get('course_cache_name')
                    )
                    st.session_state['show_solutions'] = False
                    st.rerun()
                except RuntimeError as err:
                    st.error("⏳ Les serveurs de calcul sont temporairement saturés par Google. Réessaie dans une trentaine de secondes.") 

        if 'exercises_list' in st.session_state and st.session_state['exercises_list']:
            st.divider()
            
            for i, ex in enumerate(st.session_state['exercises_list']):
                st.subheader(f"📌 {ex['title']}")
                st.markdown(ex['instructions'], unsafe_allow_html=True)
                with st.expander("💡 Coup de pouce (indice)"):
                    st.info(ex['hint'])
                st.write("")

            st.divider()

            if not st.session_state.get('show_solutions', False):
                if st.button("👁️ Afficher les corrigés détaillés"):
                    st.session_state['show_solutions'] = True
                    st.rerun()
            else:
                if st.button("🙈 Masquer les corrigés"):
                    st.session_state['show_solutions'] = False
                    st.rerun()

                st.subheader("📋 Corrigés Détaillés")
                for i, ex in enumerate(st.session_state['exercises_list']):
                    with st.expander(f"✅ Solution : {ex['title']}", expanded=True):
                        st.markdown(ex['solution'], unsafe_allow_html=True)


# TAB 4 : QUIZ & RAPPEL ACTIF
with tabs[3]:
    st.header("❓ Quiz & Validation des Connaissances")
    st.caption("Rappel actif immédiat : le meilleur moyen de fixer les notions dans ta mémoire à long terme !")

    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; font-weight:700; font-size:0.85rem; padding:6px 16px; border-radius:50px; margin-bottom:14px;">
            <span>⏱️</span> Quiz express : ~3 min • 5 questions rapides
        </div>
        """, 
        unsafe_allow_html=True
    )

    if 'course_markdown' not in st.session_state:
        st.info("Veuillez d'abord générer un cours dans le premier onglet.")
    else:
        if st.button("🎲 Générer un nouveau quiz", type="primary"):
            with st.spinner("Création du quiz en cours..."):
                quiz_agent = QuizAgent()
                st.session_state['quiz_data'] = quiz_agent.generate_quiz(st.session_state['course_markdown'],cache_name=st.session_state.get('course_cache_name'))
                st.session_state['quiz_submitted'] = False

        if 'quiz_data' in st.session_state and st.session_state['quiz_data']:
            questions = st.session_state['quiz_data']

            with st.form("quiz_form"):
                current_answers = []
                for i, q in enumerate(questions):
                    st.markdown(f"**Question {i + 1} : {q['question']}**", unsafe_allow_html=True)
                    choice = st.radio(
                        label=f"Choisis ta réponse pour la question {i + 1} :",
                        options=range(len(q['options'])),
                        format_func=lambda idx, opts=q['options']: opts[idx],
                        key=f"q_{i}",
                        index=None
                    )
                    current_answers.append(choice)
                    st.divider()

                submitted = st.form_submit_button("✅ Valider mes réponses", type="primary")

            if submitted:
                st.session_state['user_quiz_answers'] = current_answers
                st.session_state['quiz_submitted'] = True

            if st.session_state.get('quiz_submitted', False):
                saved_answers = st.session_state.get('user_quiz_answers', [])
                score = 0
                for i, q in enumerate(questions):
                    user_ans = saved_answers[i] if i < len(saved_answers) else None
                    correct_ans = q['correct_answer_index']

                    if user_ans == correct_ans:
                        score += 1
                        st.success(f"**Question {i + 1} : Bravo !**\n\n{q['explanation']}")
                    else:
                        bonne_rep_texte = q['options'][correct_ans]
                        st.error(f"**Question {i + 1} : Pas tout à fait.**\n\nLa bonne réponse était : **{bonne_rep_texte}**\n\n💡 {q['explanation']}")

                st.divider()
                if score == len(questions):
                    st.balloons()
                    st.metric("Résultat final", f"{score} / {len(questions)}", "Parfait !")
                else:
                    st.metric("Résultat final", f"{score} / {len(questions)}")
