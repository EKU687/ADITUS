"""
Vue : Administration
Gestion des utilisateurs et de l'attribution des rôles (Admin, Valideur, Demandeur).
"""

import pandas as pd
import streamlit as st
from services.db import supabase, supabase_admin


def afficher_onglet_administration():
    """Rendu du panneau d'administration des utilisateurs."""
    st.subheader("⚙️ Administration des Utilisateurs et Rôles")
    st.caption("Gérez les accès et les droits des utilisateurs du portail ADITUS.")

    # Formulaire d'ajout / modification de rôle
    with st.form("form_gestion_utilisateur", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            email_saisi = (
                st.text_input("Adresse e-mail :", placeholder="prenom.nom@gouv.nc")
                .strip()
                .lower()
            )
        with col2:
            role_selectionne = st.selectbox(
                "Rôle à attribuer :", ["Demandeur", "Valideur", "Administrateur"]
            )
        with col3:
            st.write("")
            st.write("")
            soumis = st.form_submit_button(
                "Enregistrer 💾", type="primary", use_container_width=True
            )

        if soumis:
            if not email_saisi or "@" not in email_saisi:
                st.warning("⚠️ Veuillez saisir une adresse e-mail valide.")
            else:
                try:
                    # Upsert dans la table Utilisateurs
                    donnees_user = {"email": email_saisi, "role": role_selectionne}
                    supabase.table("Utilisateurs").upsert(
                        donnees_user, on_conflict="email"
                    ).execute()
                    st.success(
                        f"✅ Rôle **{role_selectionne}** attribué avec succès à **{email_saisi}**."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur lors de la mise à jour de l'utilisateur : {e}")

    st.divider()
    st.markdown("### 📜 Liste des Utilisateurs Référencés")

    try:
        req = (
            supabase.table("Utilisateurs")
            .select("*")
            .order("email", desc=False)
            .execute()
        )
        utilisateurs = req.data if req.data else []

        if utilisateurs:
            df = pd.DataFrame(utilisateurs)
            st.dataframe(
                df[["email", "role"]], use_container_width=True, hide_index=True
            )
        else:
            st.info(
                "Aucun utilisateur spécifique n'est encore enregistré dans la table Utilisateurs."
            )
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de la liste des utilisateurs : {e}")
