"""
Vue : Espace Valideur
Permet aux responsables de site d'examiner, approuver ou refuser les demandes d'accès en attente.
"""

import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from services.db import supabase
from services.mailer import envoyer_email_decision


def obtenir_date_nc() -> datetime.date:
    """Renvoie la date actuelle à Nouméa."""
    return datetime.datetime.now(ZoneInfo("Pacific/Noumea")).date()


def charger_demandes_attente(email_valideur: str, est_admin: bool = False):
    """Récupère les demandes à valider pour les sites gérés par le valideur."""
    try:
        # Récupérer les sites autorisés pour ce valideur
        sites_autorises = []
        if not est_admin:
            req_sites = (
                supabase.table("Valideurs_sites")
                .select("site_nom")
                .ilike("valideur_email", email_valideur.strip().lower())
                .execute()
            )
            if req_sites.data:
                sites_autorises = [
                    row["site_nom"] for row in req_sites.data if row.get("site_nom")
                ]

        query = supabase.table("Demandes_acces").select("*").eq("statut", "En attente")

        if not est_admin and sites_autorises:
            query = query.in_("site_id", sites_autorises)

        req = query.order("created_at", desc=True).execute()
        return req.data if req.data else []
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des demandes en attente : {e}")
        return []


def afficher_onglet_valideur():
    """Rendu de l'Espace Valideur."""
    st.subheader("👑 Espace de Validation des Demandes")
    st.caption("Examinez et traitez les demandes d'accès soumises pour vos sites.")

    email_user = st.session_state.get("user_email", "").strip().lower()
    est_admin = st.session_state.get("is_admin", False)

    demandes = charger_demandes_attente(email_user, est_admin)

    if not demandes:
        st.info("🎉 Aucune demande d'accès en attente de validation pour le moment.")
        return

    st.markdown(f"**{len(demandes)}** demande(s) en attente de traitement :")

    for d in demandes:
        id_demande = d.get("id")
        site_nom = d.get("site_id", "Non précisé")
        demandeur = d.get("email_demandeur", "Inconnu")
        organisme = d.get("organisme", "N/C")
        motif = d.get("motif", "Non précisé")
        mode = d.get("mode_acces", "Piéton")
        nb_pers = d.get("nombre_personnes", 1)

        d_entree = d.get("date_entree", "")
        d_sortie = d.get("date_sortie", "")
        h_entree = str(d.get("heure_entree", ""))[:5]
        h_sortie = str(d.get("heure_sortie", ""))[:5]

        with st.expander(
            f"📌 Demande #{id_demande} — Site : **{site_nom}** (par {demandeur})",
            expanded=True,
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"👤 **Demandeur :** `{demandeur}`")
                st.markdown(f"🏢 **Organisme :** {organisme}")
                st.markdown(f"👥 **Effectif :** {nb_pers} personne(s)")
                st.markdown(f"📝 **Motif :** {motif}")

            with col2:
                st.markdown(f"🚶‍♂️/🚗 **Mode d'accès :** {mode}")
                if mode == "Véhicule":
                    st.markdown(
                        f"🆔 **Plaque :** `{d.get('vehicule_immatriculation', 'N/C')}`"
                    )
                    st.markdown(f"🚘 **Véhicule :** {d.get('vehicule_type', 'N/C')}")
                    st.markdown(
                        f"🪪 **Conducteur :** {d.get('vehicule_conducteur', 'N/C')}"
                    )

                st.markdown(f"📅 **Période :** Du {d_entree} au {d_sortie}")
                st.markdown(f"🕒 **Horaires :** De {h_entree} à {h_sortie}")

            st.divider()

            # Actions de Validation / Refus
            col_v, col_r, _ = st.columns([1, 1, 2])

            with col_v:
                if st.button(
                    "Valider ✅",
                    key=f"btn_val_{id_demande}",
                    type="primary",
                    use_container_width=True,
                ):
                    _traiter_decision(id_demande, "Validé", d, email_user)

            with col_r:
                with st.popover("Refuser ❌", use_container_width=True):
                    st.markdown("##### Motif du refus")
                    motif_refus = st.text_area(
                        "Explication du refus :", key=f"txt_refus_{id_demande}"
                    )
                    if st.button(
                        "Confirmer le refus",
                        key=f"btn_conf_refus_{id_demande}",
                        type="primary",
                    ):
                        if not motif_refus.strip():
                            st.warning("⚠️ Veuillez indiquer un motif de refus.")
                        else:
                            _traiter_decision(
                                id_demande,
                                "Refusé",
                                d,
                                email_user,
                                motif_refus=motif_refus.strip(),
                            )


def _traiter_decision(
    id_demande,
    statut: str,
    demande_dict: dict,
    valideur_email: str,
    motif_refus: str = None,
):
    """Met à jour le statut dans Supabase de façon sécurisée et déclenche l'e-mail de décision."""

    # 1. Préparation du dictionnaire de mise à jour minimal (100% compatible BDD)
    update_data = {"statut": statut}
    if motif_refus:
        update_data["motif_refus"] = motif_refus

    # 2. Exécution de la mise à jour
    try:
        supabase.table("Demandes_acces").update(update_data).eq(
            "id", id_demande
        ).execute()
    except Exception as e:
        err_msg = str(e)
        # Si même 'motif_refus' n'existe pas dans la table, on met à jour uniquement 'statut'
        if "motif_refus" in err_msg or "PGRST204" in err_msg:
            try:
                supabase.table("Demandes_acces").update({"statut": statut}).eq(
                    "id", id_demande
                ).execute()
            except Exception as e_inner:
                st.error(f"❌ Erreur lors de la mise à jour de la demande : {e_inner}")
                return
        else:
            st.error(f"❌ Erreur lors de la mise à jour de la demande : {e}")
            return

    st.success(f"✅ Demande #{id_demande} marquée comme **{statut}** !")

    # 3. Envoi de l'e-mail de notification au demandeur
    try:
        envoyer_email_decision(
            destinataire_email=demande_dict.get("email_demandeur"),
            site_nom=demande_dict.get("site_id", "Site GNC"),
            decision=statut,
            date_entree=demande_dict.get("date_entree"),
            heure_entree=demande_dict.get("heure_entree"),
            date_sortie=demande_dict.get("date_sortie"),
            heure_sortie=demande_dict.get("heure_sortie"),
            motif_refus=motif_refus,
        )
    except Exception as e_mail:
        st.info(
            f"ℹ️ Statut mis à jour mais avertissement notification e-mail : {e_mail}"
        )

    st.rerun()
