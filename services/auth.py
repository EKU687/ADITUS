"""
Service d'Authentification pour ADITUS.
Gère les variables de session, l'envoi/vérification d'OTP et l'écran de connexion UI.
"""

import httpx
import streamlit as st
from services.db import supabase

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
            supabase.table("Utilisateurs")
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
            supabase.table("Valideurs_sites")
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
                    try:
                        supabase.auth.sign_in_with_otp(
                            {
                                "email": email_saisi,
                                "options": {"should_create_user": True},
                            }
                        )
                        st.session_state["user_email"] = email_saisi
                        st.session_state["otp_sent"] = True
                        st.success(
                            f"Un code de vérification a été envoyé à **{email_saisi}**."
                        )
                        st.rerun()

                    except Exception as e:
                        err_str = str(e).lower()
                        if "timed out" in err_str or isinstance(
                            e, (httpx.ReadTimeout, httpx.TimeoutException)
                        ):
                            st.session_state["user_email"] = email_saisi
                            st.session_state["otp_sent"] = True
                            st.warning(
                                "⚠️ L'envoi prend du temps, mais le code a probablement été transmis. Saisissez-le ci-dessous."
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ Erreur lors de l'envoi du code : {e}")
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
                        try:
                            res = supabase.auth.verify_otp(
                                {
                                    "email": st.session_state["user_email"],
                                    "token": code_otp.strip(),
                                    "type": "email",
                                }
                            )

                            if res.session:
                                st.session_state["user_authenticated"] = True
                                st.session_state["user_email"] = res.user.email

                                est_admin, est_valideur = verifier_roles_utilisateur(
                                    res.user.email
                                )
                                st.session_state["is_admin"] = est_admin
                                st.session_state["is_valideur"] = est_valideur

                                st.success("Connexion réussie !")
                                st.rerun()
                            else:
                                st.error("❌ Code invalide ou expiré.")
                        except Exception as e:
                            st.error(f"❌ Erreur de vérification : {e}")
                    else:
                        st.warning(
                            "⚠️ Veuillez entrer au moins les 6 chiffres du code."
                        )

            with col_back:
                if st.button("Changer d'e-mail 🔄", use_container_width=True):
                    st.session_state["otp_sent"] = False
                    st.rerun()


def deconnexion():
    """Déconnecte l'utilisateur et réinitialise la session."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["user_authenticated"] = False
    st.session_state["otp_sent"] = False
    st.session_state["user_email"] = ""
    st.session_state["is_admin"] = False
    st.session_state["is_valideur"] = False
    st.rerun()
