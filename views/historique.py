"""
Vue : Suivi & Historique des demandes
Affiche l'ensemble des demandes soumises par l'utilisateur connecté.
"""

import pandas as pd
import streamlit as st
from services.db import supabase


def afficher_onglet_historique():
    """Rendu de l'historique des demandes de l'utilisateur."""
    st.subheader("📋 Suivi & Historique de vos demandes")

    email_user = st.session_state.get("user_email", "").strip().lower()

    try:
        req = (
            supabase.table("Demandes_acces")
            .select("*")
            .ilike("email_demandeur", email_user)
            .order("created_at", desc=True)
            .execute()
        )

        demandes = req.data if req.data else []

        if not demandes:
            st.info("ℹ️ Vous n'avez formulé aucune demande d'accès pour le moment.")
            return

        df = pd.DataFrame(demandes)

        # Sélection et renommage des colonnes pour un affichage propre
        colonnes_visibles = {
            "site_id": "Site",
            "mode_acces": "Mode",
            "statut": "Statut",
            "date_entree": "Début",
            "date_sortie": "Fin",
            "vehicule_immatriculation": "Immatriculation",
            "created_at": "Date demande",
        }

        cols_existantes = [c for c in colonnes_visibles.keys() if c in df.columns]
        df_display = df[cols_existantes].rename(columns=colonnes_visibles)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de l'historique : {e}")
