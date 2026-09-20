import datetime
import streamlit as st
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# Adresse expéditeur validée sur ton compte Brevo
EXPEDITEUR_ADITUS = "notification.aditus@gmail.com"


def _get_brevo_api_instance():
    """Initialise l'instance d'API Brevo en récupérant la clé depuis les secrets Streamlit."""
    api_key = st.secrets.get("BREVO_API_KEY", "").strip()
    if not api_key:
        st.error("⚠️ Clé BREVO_API_KEY manquante dans les secrets.")
        return None

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    return sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )


def _formater_date_fr(date_val) -> str:
    """Helper interne : convertit de manière sécurisée une date (str, datetime.date ou None) au format JJ/MM/AAAA."""
    if not date_val:
        return "N/C"
    if isinstance(date_val, (datetime.date, datetime.datetime)):
        return date_val.strftime("%d/%m/%Y")
    if isinstance(date_val, str) and len(date_val) >= 10:
        return f"{date_val[8:10]}/{date_val[5:7]}/{date_val[0:4]}"
    return str(date_val)


def envoyer_email_notification(
    destinataire_email: str,
    site_nom: str,
    demandeur_email: str,
    motif_demande: str = "Motif non précisé",
) -> bool:
    """Envoie une notification par e-mail au valideur du site lors d'une nouvelle demande d'accès."""
    api_instance = _get_brevo_api_instance()
    if not api_instance:
        return False

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #0056b3;">Nouvelle demande d'accès en attente de validation</h2>
        <p>Bonjour,</p>
        <p>Une nouvelle demande d'accès vient d'être soumise pour le site <strong>{site_nom}</strong>.</p>
        <table style="border-collapse: collapse; margin: 15px 0;">
          <tr><td style="padding: 5px; font-weight: bold;">Demandeur :</td><td style="padding: 5px;">{demandeur_email}</td></tr>
          <tr><td style="padding: 5px; font-weight: bold;">Motif :</td><td style="padding: 5px;">{motif_demande}</td></tr>
        </table>
        <p>Veuillez vous connecter sur le portail <strong>GNC-PASS</strong> pour valider ou refuser cette demande.</p>
        <hr style="border: none; border-top: 1px solid #ccc; margin-top: 20px;">
        <p style="font-size: 12px; color: #777;">Ceci est un message automatique envoyé par le système GNC-PASS.</p>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": destinataire_email}],
        sender={"name": "Portail ADITUS (GNC)", "email": EXPEDITEUR_ADITUS},
        reply_to={"email": demandeur_email, "name": "Demandeur GNC-PASS"},
        subject=f"🔔 [GNC-PASS] Nouvelle demande d'accès - Site {site_nom}",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        st.toast(f"📧 Notification transmise à {destinataire_email}", icon="📩")
        return True
    except ApiException as e:
        st.warning(
            f"⚠️ La demande a été enregistrée, mais l'e-mail n'a pas pu être envoyé : {e}"
        )
        return False


def envoyer_email_decision(
    destinataire_email: str,
    site_nom: str,
    decision: str,
    date_entree=None,
    heure_entree=None,
    date_sortie=None,
    heure_sortie=None,
    motif_refus: str = None,
) -> bool:
    """Envoie l'e-mail de décision (Accord ou Refus d'accès) au demandeur."""
    api_instance = _get_brevo_api_instance()
    if not api_instance:
        return False

    d_ent_fr = _formater_date_fr(date_entree)
    d_sor_fr = _formater_date_fr(date_sortie)

    heure_e_str = str(heure_entree)[:-3] if heure_entree else ""
    heure_s_str = str(heure_sortie)[:-3] if heure_sortie else ""

    if decision == "Validé":
        sujet = f"✅ [GNC-PASS] Demande d'accès ACCORDÉE - Site {site_nom}"
        couleur_titre = "#28a745"
        texte_decision = f"""
        <p style='font-size: 16px;'>Votre demande d'accès a été <strong>APPROUVÉE</strong>.</p>
        <div style='background-color: #f8f9fa; border-left: 4px solid #28a745; padding: 12px; margin: 15px 0;'>
            <h4 style='margin: 0 0 10px 0; color: #28a745;'>📋 Rappel de votre autorisation d'accès :</h4>
            <ul style='margin: 0; padding-left: 20px;'>
                <li><strong>Site concerné :</strong> {site_nom}</li>
                <li><strong>Début d'accès :</strong> le {d_ent_fr} à {heure_e_str}</li>
                <li><strong>Fin d'accès :</strong> le {d_sor_fr} à {heure_s_str}</li>
            </ul>
        </div>
        <p>Vous pouvez désormais vous présenter sur le site aux créneaux indiqués.</p>
        """
    else:
        sujet = f"❌ [GNC-PASS] Demande d'accès REFUSÉE - Site {site_nom}"
        couleur_titre = "#dc3545"
        texte_decision = f"""
        <p style='font-size: 16px;'>Votre demande d'accès pour le site <strong>{site_nom}</strong> a été <strong>REFUSÉE</strong>.</p>
        <p><strong>Motif du refus :</strong> {motif_refus if motif_refus else 'Non précisé'}</p>
        """

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: {couleur_titre};">Mise à jour de votre demande d'accès</h2>
        <p>Bonjour,</p>
        {texte_decision}
        <hr style="border: none; border-top: 1px solid #ccc; margin-top: 20px;">
        <p style="font-size: 12px; color: #777;">Ceci est un message automatique envoyé par le système GNC-PASS.</p>
      </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": destinataire_email}],
        sender={"name": "Portail ADITUS (GNC)", "email": EXPEDITEUR_ADITUS},
        reply_to={"email": "eric.kuter@gouv.nc", "name": "Éric Kuter - GNC"},
        subject=sujet,
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        st.toast(f"📧 Décision transmise par e-mail à {destinataire_email}", icon="📩")
        return True
    except ApiException as e:
        st.warning(
            f"⚠️ La décision a été enregistrée, mais l'e-mail n'a pas pu être envoyé : {e}"
        )
        return False
