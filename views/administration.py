"""
Vue : Administration - Gestion des Valideurs par Site
Permet de configurer l'adresse e-mail du responsable valideur pour chaque bâtiment/site GNC (identifié par son code_site).
"""

import pandas as pd
import streamlit as st
from services.db import supabase


def charger_liste_codes_sites() -> list:
    """Récupère la liste dynamique des codes de sites actifs depuis la table 'Sites'."""
    try:
        req = (
            supabase.table("Sites")
            .select("code_site")
            .eq("actif", True)
            .order("code_site", desc=False)
            .execute()
        )

        if req.data:
            codes = [row["code_site"] for row in req.data if row.get("code_site")]
            if codes:
                return codes
    except Exception as e:
        st.warning(f"⚠️ Erreur lors de la lecture des codes de sites : {e}")

    # Valeurs de secours par défaut
    return ["DINUM", "DOUMER", "DSF", "OUEMO", "HABITAT"]


def charger_assignations_valideurs():
    """Récupère la liste des assignations site <-> valideur depuis Supabase."""
    try:
        req = (
            supabase.table("Valideurs_sites")
            .select("id, site_nom, valideur_email")
            .execute()
        )
        if req.data:
            return req.data
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture des valideurs : {e}")
    return []


def afficher_onglet_administration():
    """Rendu du panneau d'administration des valideurs par site."""
    st.subheader("⚙️ Gestion des Valideurs par Site")
    st.info(
        "💡 Espace réservé aux administrateurs pour configurer qui valide l'accès à quel bâtiment."
    )

    liste_codes_sites = charger_liste_codes_sites()

    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("### ➕ Assigner un valideur")
        with st.form("form_assigner_valideur", clear_on_submit=True):
            site_sel = st.selectbox(
                "Sélectionnez le code du site :",
                ["Sélectionnez un site..."] + liste_codes_sites,
            )
            email_valideur = (
                st.text_input(
                    "Email du responsable (Valideur) :",
                    placeholder="prenom.nom@gouv.nc",
                )
                .strip()
                .lower()
            )

            submitted = st.form_submit_button(
                "Enregistrer le valideur 💾", type="primary"
            )

            if submitted:
                if site_sel == "Sélectionnez un site...":
                    st.warning("⚠️ Veuillez sélectionner un site.")
                elif not email_valideur or "@" not in email_valideur:
                    st.warning("⚠️ Veuillez indiquer une adresse e-mail valide.")
                else:
                    try:
                        # Recherche basée uniquement sur la colonne existante site_nom
                        req_exist = (
                            supabase.table("Valideurs_sites")
                            .select("id")
                            .eq("site_nom", site_sel)
                            .execute()
                        )

                        donnees_maj = {
                            "site_nom": site_sel,
                            "valideur_email": email_valideur,
                        }

                        if req_exist.data and len(req_exist.data) > 0:
                            # Mise à jour de la ligne existante
                            row_id = req_exist.data[0]["id"]
                            supabase.table("Valideurs_sites").update(donnees_maj).eq(
                                "id", row_id
                            ).execute()
                        else:
                            # Création d'une nouvelle assignation
                            supabase.table("Valideurs_sites").insert(
                                donnees_maj
                            ).execute()

                        st.success(
                            f"✅ Valideur **{email_valideur}** assigné au site **{site_sel}**."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enregistrement : {e}")

    with c_right:
        st.markdown("### 📋 Liste des assignations actuelles")
        assignations = charger_assignations_valideurs()

        if assignations:
            df = pd.DataFrame(assignations)
            if "site_nom" in df.columns and "valideur_email" in df.columns:
                df_display = df[["site_nom", "valideur_email"]].rename(
                    columns={
                        "site_nom": "Code Site",
                        "valideur_email": "Email du Valideur",
                    }
                )
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.write("Aucune assignation trouvée dans la base.")
