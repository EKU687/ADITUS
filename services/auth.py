"""
Service d'Authentification pour ADITUS.
Gère les variables de session, l'envoi/vérification d'OTP et l'écran de connexion UI.
"""

import streamlit as st
from services.db import supabase, supabase_admin
from services.mailer import envoyer_email_otp
from services.otp import generer_otp, verifier_otp

# Liste des e-mails administrateurs principaux par défaut
ADMINS_SYSTEME = ["eric.kuter@gouv.nc"]


def verifier_roles_utilisateur(email: str):
    """Consulte la base pour déterminer si l'utilisateur est admin ou valideur."""
    if not email:
        return False, False

    email_clean = email.strip().lower()

    # Si c'est l'administrateur principal
    if email_clean in ADMINS_SYSTEME:
        return True, True

    try:
        # Vérification dans la table Utilisateurs ou Valideurs
        req = (
            supabase_admin.table("Utilisateurs")
            .select("role")
            .ilike("email", email_clean)
            .execute()
        )

        if req.data and len(req.data) > 0:
            role_db = str(req.data[0].get("role", "")).strip().lower()
            est_admin = role_db in ["administrateur", "admin"]
            est_valideur = role_db in ["valideur", "administrateur", "admin"]
            return est_admin, est_valideur

        # Vérification alternative si l'utilisateur est enregistré comme valideur d'au moins un site
        req_valideur = (
            supabase_admin.table("Valideurs_sites")
            .select("site_id")
            .ilike("email_valideur", email_clean)
            .execute()
        )

        if req_valideur.data and len(req_valideur.data) > 0:
            return False, True

    except Exception as e:
        st.warning(f"⚠️ Erreur lors de la vérification des rôles : {e}")

    return False, False


def initialiser_session_auth():
    """Initialise les clés de session d'authentification."""
    if "user_authenticated" not in st.session_state:
        st.session_state["user_authenticated"] = False
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = ""
    if "otp_sent" not in st.session_state:
        st.session_state["otp_sent"] = False
    if "otp_record" not in st.session_state:
        st.session_state["otp_record"] = None
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False
    if "is_valideur" not in st.session_state:
        st.session_state["is_valideur"] = False


def afficher_ecran_connexion():
    """Affiche l'interface de connexion OTP Streamlit."""
    st.title("🏢 PORTAIL GNC-PASS — Connexion Sécurisée")
    st.markdown(
        "Veuillez vous authentifier avec votre adresse e-mail professionnelle pour accéder aux services."
    )
    st.divider()

    col_login, _ = st.columns([1, 1])

    with col_login:
        if not st.session_state["otp_sent"]:
            st.subheader("🔑 Connexion par e-mail")
            email_saisi = st.text_input(
                "Adresse e-mail professionnelle", placeholder="prenom.nom@gouv.nc"
            )

            if st.button(
                "Envoyer le code de vérification 📩",
                type="primary",
                use_container_width=True,
            ):
                if email_saisi and "@" in email_saisi:
                    nouveau_code, otp_record = generer_otp()
                    if envoyer_email_otp(email_saisi, nouveau_code):
                        st.session_state["user_email"] = email_saisi
                        st.session_state["otp_record"] = otp_record
                        st.session_state["otp_sent"] = True
                        st.success(
                            f"Un code de vérification a été envoyé à **{email_saisi}** (valable 10 minutes)."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "❌ Erreur lors de l'envoi du code : vérifiez la clé BREVO_API_KEY "
                            "et que l'adresse expéditrice est validée sur Brevo."
                        )
                else:
                    st.warning("⚠️ Veuillez saisir une adresse e-mail valide.")

        else:
            st.subheader("📩 Saisissez votre code")
            st.info(f"Code transmis à : **{st.session_state['user_email']}**")

            code_otp = st.text_input(
                "Code de vérification", max_chars=8, placeholder="12345678"
            )

            col_val, col_back = st.columns([1, 1])
            with col_val:
                if st.button(
                    "Valider et accéder 🚀", type="primary", use_container_width=True
                ):
                    if code_otp and len(code_otp.strip()) >= 6:
                        valide, raison = verifier_otp(
                            code_otp, st.session_state.get("otp_record")
                        )
                        if valide:
                            email = st.session_state["user_email"]
                            st.session_state["user_authenticated"] = True

                            est_admin, est_valideur = verifier_roles_utilisateur(email)
                            st.session_state["is_admin"] = est_admin
                            st.session_state["is_valideur"] = est_valideur

                            st.success("Connexion réussie !")
                            st.rerun()
                        elif raison == "expired":
                            st.error(
                                "❌ Code expiré (valable 10 minutes). Demandez un nouveau code."
                            )
                        elif raison == "too_many":
                            st.error(
                                "❌ Trop de tentatives incorrectes. Demandez un nouveau code."
                            )
                        else:
                            st.error("❌ Code incorrect.")
                    else:
                        st.warning(
                            "⚠️ Veuillez entrer au moins les 6 chiffres du code."
                        )

            with col_back:
                if st.button("Changer d'e-mail 🔄", use_container_width=True):
                    st.session_state["otp_sent"] = False
                    st.session_state["otp_record"] = None
                    st.rerun()


def deconnexion():
    """Déconnecte l'utilisateur et réinitialise la session."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["user_authenticated"] = False
    st.session_state["otp_sent"] = False
    st.session_state["otp_record"] = None
    st.session_state["user_email"] = ""
    st.session_state["is_admin"] = False
    st.session_state["is_valideur"] = False
    st.rerun()
