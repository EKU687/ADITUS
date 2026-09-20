"""
Vue : Espace Valideur
Permet aux valideurs et administrateurs d'examiner, approuver ou refuser les demandes d'accès.
"""

import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from services.db import supabase, supabase_admin
from services.mailer import envoyer_email_decision


def afficher_onglet_valideur():
    """Rendu de l'espace de validation des demandes."""
    st.subheader("⚖️ Espace de Validation des Demandes")
    st.caption("Examinez les demandes en attente et traitez-les.")

    try:
        # Récupération des demandes en attente
        req = (
            supabase.table("Demandes_acces")
            .select("*")
            .eq("statut", "En attente")
            .order("created_at", desc=False)
            .execute()
        )

        demandes_en_attente = req.data if req.data else []

        if not demandes_en_attente:
            st.success("🎉 Aucune demande en attente de validation pour le moment.")
            return

        st.info(
            f"📋 **{len(demandes_en_attente)}** demande(s) en attente de traitement."
        )

        for d in demandes_en_attente:
            id_demande = d.get("id")
            email_demandeur = d.get("email_demandeur")
            site_id = d.get("site_id")

            with st.expander(
                f"📌 Demande #{id_demande} — Site : {site_id} | Demandeur : {email_demandeur}",
                expanded=True,
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"👤 **Demandeur :** {email_demandeur}")
                    st.markdown(f"🏢 **Organisme :** {d.get('organisme')}")
                    st.markdown(f"📝 **Motif :** {d.get('motif')}")
                    st.markdown(f"🚶‍♂️ / 🚗 **Mode d'accès :** {d.get('mode_acces')}")

                with col2:
                    st.markdown(
                        f"📅 **Période :** Du {d.get('date_entree')} au {d.get('date_sortie')}"
                    )
                    st.markdown(
                        f"🕒 **Horaires :** De {str(d.get('heure_entree'))[:5]} à {str(d.get('heure_sortie'))[:5]}"
                    )
                    if d.get("mode_acces") == "Véhicule":
                        st.markdown(
                            f"🆔 **Plaque :** `{d.get('vehicule_immatriculation')}`"
                        )
                        st.markdown(f"🚘 **Véhicule :** {d.get('vehicule_type')}")
                        st.markdown(
                            f"🪪 **Conducteur :** {d.get('vehicule_conducteur')}"
                        )

                st.divider()

                col_btn_val, col_btn_ref, col_motif = st.columns([1, 1, 2])
                motif_refus_input = col_motif.text_input(
                    "Motif en cas de refus :", key=f"refus_motif_{id_demande}"
                )

                with col_btn_val:
                    if st.button(
                        "Valider ✅",
                        key=f"btn_valider_{id_demande}",
                        type="primary",
                        use_container_width=True,
                    ):
                        traiter_decision(d, "Validé", "")

                with col_btn_ref:
                    if st.button(
                        "Refuser ❌",
                        key=f"btn_refuser_{id_demande}",
                        use_container_width=True,
                    ):
                        if not motif_refus_input.strip():
                            st.warning("⚠️ Veuillez indiquer un motif de refus.")
                        else:
                            traiter_decision(d, "Refusé", motif_refus_input.strip())

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des demandes à valider : {e}")


def traiter_decision(demande: dict, nouveau_statut: str, motif_refus: str = ""):
    """Met à jour le statut dans Supabase et envoie un e-mail de notification au demandeur."""
    id_demande = demande.get("id")
    email_valideur = st.session_state.get("user_email", "").strip().lower()

    update_data = {
        "statut": nouveau_statut,
        "valideur_email": email_valideur,
        "date_validation": datetime.datetime.now(
            ZoneInfo("Pacific/Noumea")
        ).isoformat(),
    }
    if motif_refus:
        update_data["motif_refus"] = motif_refus

    try:
        supabase.table("Demandes_acces").update(update_data).eq(
            "id", id_demande
        ).execute()
        st.success(
            f" Statut mis à jour : **{nouveau_statut}** pour la demande #{id_demande}."
        )

        # Envoi de l'e-mail de décision via Brevo
        try:
            envoyer_email_decision(demande, nouveau_statut, motif_refus)
        except Exception as e_mail:
            st.info(
                f"ℹ️ Statut mis à jour mais erreur lors de l'envoi de l'e-mail : {e_mail}"
            )

        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur lors de la mise à jour de la demande : {e}")
