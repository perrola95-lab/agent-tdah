# utils/reading_tools.py
import re
import streamlit as st

def apply_bionic_reading_to_html(html_content: str) -> str:
    """Met en gras le début de chaque mot en dehors des balises HTML pour guider le regard (Bionic Reading)."""
    if not html_content:
        return ""

    # Découpage pour séparer les balises HTML du texte visible
    parts = re.split(r'(<[^>]+>)', html_content)
    bionic_parts = []

    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            # Balise HTML intacte
            bionic_parts.append(part)
        else:
            # Texte visible : traiter chaque mot
            def bionify_word(match):
                word = match.group(0)
                length = len(word)
                if length <= 3:
                    bold_len = 1
                elif length <= 6:
                    bold_len = 2
                elif length <= 9:
                    bold_len = 3
                else:
                    bold_len = 4
                return f"<b>{word[:bold_len]}</b>{word[bold_len:]}"

            # Remplacer les mots de 2 lettres ou plus (alphanumériques français)
            bionic_text = re.sub(r'\b[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]{2,}\b', bionify_word, part)
            bionic_parts.append(bionic_text)

    return "".join(bionic_parts)

def get_reading_styles(font_size_mode: str = "normal", is_dys_mode: bool = False) -> str:
    """Retourne les règles CSS injectables pour le confort de lecture."""
    font_sizes = {
        "normal": "1.05rem",
        "large": "1.2rem",
        "xlarge": "1.35rem"
    }
    size_val = font_sizes.get(font_size_mode, "1.05rem")
    line_height = "1.8" if font_size_mode != "normal" else "1.65"

    dys_import = ""
    dys_font = ""
    if is_dys_mode:
        dys_import = "@import url('https://fonts.cdnfonts.com/css/open-dyslexic');"
        dys_font = "font-family: 'OpenDyslexic', sans-serif !important;"

    return f"""
    <style>
    {dys_import}
    .course-reading-container {{
        font-size: {size_val} !important;
        line-height: {line_height} !important;
        {dys_font}
    }}
    .course-reading-container p, 
    .course-reading-container li, 
    .course-reading-container blockquote {{
        font-size: {size_val} !important;
        line-height: {line_height} !important;
        {dys_font}
    }}
    </style>
    """

def render_accessibility_toolbar():
    """Barre d'outils discrète et ergonomique au-dessus de la fiche de cours."""
    if 'reading_font_size' not in st.session_state:
        st.session_state['reading_font_size'] = 'normal'
    if 'is_dys_mode' not in st.session_state:
        st.session_state['is_dys_mode'] = False
    if 'is_bionic_mode' not in st.session_state:
        st.session_state['is_bionic_mode'] = False

    col_tools, col_bionic, col_dys = st.columns([1.5, 1.2, 1.2], vertical_alignment="center")

    with col_tools:
        st.caption("👓 **Confort de lecture :**")
        sub_c1, sub_c2, sub_c3 = st.columns(3)
        with sub_c1:
            if st.button("A", key="btn_font_normal", help="Taille normale", use_container_width=True):
                st.session_state['reading_font_size'] = 'normal'
                st.rerun()
        with sub_c2:
            if st.button("A+", key="btn_font_large", help="Taille agrandie", use_container_width=True):
                st.session_state['reading_font_size'] = 'large'
                st.rerun()
        with sub_c3:
            if st.button("A++", key="btn_font_xlarge", help="Taille maximale", use_container_width=True):
                st.session_state['reading_font_size'] = 'xlarge'
                st.rerun()

    with col_bionic:
        st.caption("⚡ **Mode Ancrage :**")
        bionic_label = "✅ Bionic actif" if st.session_state['is_bionic_mode'] else "⚡ Bionic Reading"
        if st.button(bionic_label, key="btn_toggle_bionic", use_container_width=True, help="Met en valeur les premières lettres pour éviter de décrocher"):
            st.session_state['is_bionic_mode'] = not st.session_state['is_bionic_mode']
            st.rerun()

    with col_dys:
        st.caption("📖 **Police Spéciale :**")
        dys_label = "✅ Mode Dys actif" if st.session_state['is_dys_mode'] else "📖 Police Dyslexie"
        if st.button(dys_label, key="btn_toggle_dys", use_container_width=True, help="Active la police OpenDyslexic"):
            st.session_state['is_dys_mode'] = not st.session_state['is_dys_mode']
            st.rerun()
