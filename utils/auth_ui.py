import streamlit as st
from services.auth_service import AuthService

def render_auth_page():
    """Affiche la page d'accueil avec formulaire de connexion et d'inscription."""
    auth_service = AuthService()

    # Conteneur centré élégant
    col_left, col_center, col_right = st.columns([1, 2.2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-size: 2.8rem; margin-bottom: 8px;">🧠</div>
                <h2 style="color: #1e1b4b; font-weight: 800; font-size: 1.8rem; margin: 0;">Coach d'Apprentissage TDAH</h2>
                <p style="color: #64748b; font-size: 0.95rem; margin-top: 6px;">
                    Espace personnalisé de révision et de réussite scolaire (Collège 4ème)
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        tab_login, tab_register = st.tabs(["🔑 Se connecter", "✨ Créer un compte"])

        with tab_login:
            st.write("")
            with st.form("login_form"):
                email = st.text_input("Adresse e-mail :", placeholder="ex: chloe@college.fr").strip()
                password = st.text_input("Mot de passe :", type="password", placeholder="••••••••")
                
                st.write("")
                submit_login = st.form_submit_button("🚀 Me connecter", type="primary", use_container_width=True)

            if submit_login:
                if not email or not password:
                    st.warning("Veuillez renseigner votre adresse e-mail et votre mot de passe.")
                else:
                    res = auth_service.authenticate_user(email, password)
                    if not res["success"]:
                        st.error(res["error"])
                    else:
                        user = res["user"]
                        if not user["is_approved"]:
                            st.info(
                                "⏳ **Inscription enregistrée !**\n\n"
                                "Ton compte est actuellement **en attente de validation par l'administrateur**.\n\n"
                                "Reviens très vite dès que ton accès aura été activé !"
                            )
                        else:
                            st.session_state["authenticated"] = True
                            st.session_state["user"] = user
                            st.success(f"Bienvenue, {user['name']} !")
                            st.rerun()

        with tab_register:
            st.write("")
            # Information sur le premier compte / inscription
            if auth_service.get_user_count() == 0:
                st.info("👑 **Initialisation :** Le premier compte créé recevra automatiquement les droits **Administrateur**.")

            with st.form("register_form"):
                name = st.text_input("Prénom ou Pseudo :", placeholder="ex: Chloé").strip()
                email_reg = st.text_input("Adresse e-mail :", placeholder="ex: chloe@college.fr").strip()
                pwd1 = st.text_input("Mot de passe (6 caractères min.) :", type="password", placeholder="••••••••")
                pwd2 = st.text_input("Confirmez le mot de passe :", type="password", placeholder="••••••••")
                
                st.caption("🔒 Vos identifiants sont cryptés et stockés de façon sécurisée.")
                st.write("")
                submit_register = st.form_submit_button("🎉 Créer mon compte", type="primary", use_container_width=True)

            if submit_register:
                if not email_reg or not pwd1:
                    st.warning("Veuillez renseigner un e-mail et un mot de passe.")
                elif pwd1 != pwd2:
                    st.error("Les deux mots de passe ne correspondent pas.")
                elif len(pwd1) < 6:
                    st.error("Le mot de passe doit comporter au moins 6 caractères.")
                else:
                    res = auth_service.register_user(email=email_reg, password=pwd1, name=name)
                    if not res["success"]:
                        st.error(res["error"])
                    else:
                        user = res["user"]
                        if user["is_admin"]:
                            st.success("👑 **Compte Administrateur créé avec succès !** Connexion en cours...")
                            st.session_state["authenticated"] = True
                            st.session_state["user"] = user
                            st.rerun()
                        else:
                            st.success("🎉 **Compte créé avec succès !**")
                            st.info(
                                "⏳ Ton compte a bien été enregistré. Il est maintenant **en attente d'acceptation par l'administrateur**.\n\n"
                                "Tu pourras te connecter dès que ton accès aura été validé !"
                            )
