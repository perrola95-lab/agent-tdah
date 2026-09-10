# utils/theme.py
import streamlit as st

CUSTOM_CSS = """
<style>
/* --- 1. TYPOGRAPHIE GOOGLE FONTS (PLUS JAKARTA SANS & MATERIAL ICONS) --- */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

html, body, .stApp, p, h1, h2, h3, h4, h5, h6, .stMarkdown, .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label, div[data-testid="stTabs"] button {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Protection impérative des icônes natives Streamlit (Material Symbols Rounded) */
span[data-testid="stIconMaterial"],
span[class*="e1vmumty"],
.material-symbols-rounded,
.material-icons,
[data-testid*="stIcon"] {
    font-family: 'Material Symbols Rounded' !important;
    font-style: normal !important;
    font-weight: normal !important;
    font-feature-settings: 'liga' 1 !important;
    -webkit-font-feature-settings: 'liga' 1 !important;
    text-transform: none !important;
    display: inline-flex !important;
    align-items: center !important;
    line-height: 1 !important;
}

/* --- CORRECTION DU CHARGEUR DE FICHIERS (ZONE DE DÉPÔT & BOUTON) --- */
section[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed #cbd5e1 !important;
    border-radius: 14px !important;
    background: #f8fafc !important;
    padding: 12px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    transition: all 0.2s ease !important;
}

section[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #818cf8 !important;
    background: #f1f5f9 !important;
}

/* Bouton principal du chargeur de fichier (uniquement quand la zone est vide / hors liste de fichiers) */
section[data-testid="stFileUploaderDropzone"] > span button,
section[data-testid="stFileUploaderDropzone"] span[class*="e3v525e6"] button {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 10px !important;
    padding: 8px 18px !important;
    white-space: nowrap !important;
    background: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

section[data-testid="stFileUploaderDropzone"] > span button:hover,
section[data-testid="stFileUploaderDropzone"] span[class*="e3v525e6"] button:hover {
    border-color: #6366f1 !important;
    background: #f8fafc !important;
    box-shadow: 0 3px 8px rgba(79, 70, 229, 0.15) !important;
    transform: translateY(-1px) !important;
}

/* 1. Masquage du contenu interne uniquement pour le bouton principal */
section[data-testid="stFileUploaderDropzone"] > span button *,
section[data-testid="stFileUploaderDropzone"] span[class*="e3v525e6"] button * {
    display: none !important;
}

/* 2. Affichage unique et garanti d'un libellé propre en français pour le bouton principal */
section[data-testid="stFileUploaderDropzone"] > span button::after,
section[data-testid="stFileUploaderDropzone"] span[class*="e3v525e6"] button::after {
    content: "📁 Parcourir les fichiers" !important;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

section[data-testid="stFileUploaderDropzone"] > span button:hover::after,
section[data-testid="stFileUploaderDropzone"] span[class*="e3v525e6"] button:hover::after {
    color: #4f46e5 !important;
}

/* --- BOUTONS DE SUPPRESSION DES FICHIERS AJOUTÉS (PROTECTION & STYLE) --- */
div[data-testid="stFileChipDeleteBtn"] button {
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
    padding: 4px 6px !important;
    border-radius: 6px !important;
    color: #94a3b8 !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stFileChipDeleteBtn"] button:hover {
    background: #fee2e2 !important;
    color: #ef4444 !important;
}




/* --- 2. ESPACEMENT ET STRUCTURE DE PAGE --- */
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1250px !important;
}

/* --- 3. HERO BANNER PRINCIPALE --- */
.hero-banner {
    background: linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(124, 58, 237, 0.06) 50%, rgba(236, 72, 153, 0.05) 100%);
    border: 1px solid rgba(99, 102, 241, 0.18);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px -2px rgba(99, 102, 241, 0.06);
    position: relative;
    overflow: hidden;
}

.hero-banner::after {
    content: '';
    position: absolute;
    top: -50px;
    right: -50px;
    width: 150px;
    height: 150px;
    background: radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, rgba(255,255,255,0) 70%);
    border-radius: 50%;
    pointer-events: none;
}

.hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: #ffffff;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 12px;
    border-radius: 50px;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
}

.hero-title {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    line-height: 1.25 !important;
    margin: 0 0 8px 0 !important;
    background: linear-gradient(135deg, #1e1b4b 0%, #3730a3 50%, #4f46e5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-subtitle {
    font-size: 1.02rem;
    color: #475569;
    margin: 0;
    line-height: 1.5;
    font-weight: 500;
}

/* --- 4. BARRE D'ONGLETS MODERNE (PILLS STYLISÉS) --- */
div[data-testid="stTabs"] {
    margin-top: 0.8rem;
    margin-bottom: 1.8rem;
}

div[data-testid="stTabs"] > div:first-child {
    background: #f1f5f9;
    padding: 6px;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    gap: 6px;
}

div[data-testid="stTabs"] button[data-baseweb="tab"] {
    border-radius: 12px !important;
    padding: 10px 18px !important;
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    color: #64748b !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    color: #4f46e5 !important;
    background: rgba(255, 255, 255, 0.8) !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.28) !important;
}

div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}

/* --- 5. BOUTONS MODERNES --- */
div.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 10px 20px !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1.5px solid transparent !important;
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.25) !important;
}

div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.38) !important;
}

div.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #334155 !important;
    border: 1.5px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}

div.stButton > button[kind="secondary"]:hover {
    border-color: #cbd5e1 !important;
    background: #f8fafc !important;
    color: #1e293b !important;
    transform: translateY(-1px) !important;
}

div.stDownloadButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    padding: 10px 18px !important;
    transition: all 0.2s ease !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #334155 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}

div.stDownloadButton > button:hover {
    border-color: #6366f1 !important;
    color: #4f46e5 !important;
    background: #f5f7ff !important;
    transform: translateY(-1px) !important;
}

/* --- 6. FORMULAIRES, INPUTS & SELECTS --- */
div[data-baseweb="select"] > div {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    background-color: #ffffff !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="select"] > div:hover {
    border-color: #cbd5e1 !important;
}

div[data-baseweb="select"] > div:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

div[data-baseweb="input"] {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    background-color: #ffffff !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

div[data-baseweb="textarea"] {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    background-color: #ffffff !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="textarea"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

section[data-testid="stFileUploaderDropzone"] {
    background: #ffffff !important;
    border: 1.5px dashed #cbd5e1 !important;
    border-radius: 14px !important;
    padding: 18px !important;
    transition: all 0.2s ease !important;
}

section[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #6366f1 !important;
    background: #f8fafc !important;
}


/* --- 7. CARTES DE CHAT & DIALOGUE COACH --- */
div[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
div[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) {
    background: #f5f7ff !important;
    border: 1px solid #e0e7ff !important;
    border-left: 4px solid #6366f1 !important;
}

div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
}

/* --- 8. CARTES DE COURS & CONTENU PÉDAGOGIQUE --- */
blockquote {
    border-left: 4px solid #6366f1 !important;
    background: #f8fafc !important;
    padding: 14px 20px !important;
    margin: 18px 0 !important;
    border-radius: 0 12px 12px 0 !important;
    color: #334155 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
}

h1, h2, h3, h4 {
    color: #1e1b4b !important;
    font-weight: 700 !important;
}

h2 {
    margin-top: 1.8rem !important;
    margin-bottom: 0.8rem !important;
    border-bottom: 2px solid #f1f5f9 !important;
    padding-bottom: 6px !important;
}

/* Ligne de séparation élégante */
hr {
    border: 0 !important;
    height: 1px !important;
    background: linear-gradient(to right, transparent, #e2e8f0, transparent) !important;
    margin: 2rem 0 !important;
}

/* Cartes de résultats & métriques */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
</style>
"""

def apply_theme():
    """Injecte la feuille de style globale dans l'application Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_hero_banner():
    """Affiche la bannière d'en-tête moderne, aérée et colorée."""
    hero_html = """
    <div class="hero-banner">
        <div class="hero-tag">🎓 Programme Collège 4ème • Méthode Adaptée TDAH</div>
        <h1 class="hero-title">Coach d'Apprentissage Interactif</h1>
        <p class="hero-subtitle">Des fiches ultra-claires, une carte mentale colorée et un guidage pas-à-pas pour apprendre avec plaisir et sans stress !</p>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)
