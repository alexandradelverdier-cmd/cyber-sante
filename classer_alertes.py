import datetime
import json
import os
import pathlib
import time

from google import genai

MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
ENTREE = pathlib.Path("a_classer.json")
SORTIE = pathlib.Path("classifications.jsonl")
TAILLE_PAQUET = 10

PROMPT = """
Tu es analyste cybersecurite pour un etablissement de sante francais (hopital, clinique).
Pour chaque alerte de vulnerabilite ci-dessous, renvoie une liste JSON avec, par alerte :
- "id_alerte" : recopie l'identifiant
- "type_faille" : execution_code | elevation_privileges | contournement_authentification |
  deni_service | fuite_donnees | autre
- "gravite" : critique | haute | moyenne | faible
- "exploitee" : oui | non | inconnu (oui UNIQUEMENT si le texte dit qu'elle est exploitee)
- "categorie_si" : acces_distant_vpn | messagerie | poste_travail_navigateur |
  serveur_web_applicatif | base_donnees | equipement_reseau | logiciel_metier_sante |
  imagerie_medicale | outil_developpement | autre
- "pertinence_hopital" : haute | moyenne | faible
  (haute = logiciel tres courant en etablissement de sante ou expose sur Internet)
- "justification" : une phrase de 20 mots maximum

Ne te fonde que sur le titre et le resume. N'invente rien.

ALERTES :
{alertes}
"""


def appeler(client, prompt):
    for essai in range(1, 6):
        try:
            reponse = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return json.loads(reponse.text)
        except Exception as e:
            attente = 15 * essai
            print(f"  Erreur ({type(e).__name__}), nouvel essai dans {attente} s ({essai}/5)")
            time.sleep(attente)
    raise SystemExit("Echec apres 5 essais. Les paquets deja traites sont sauvegardes.")


def main():
    alertes = json.loads(ENTREE.read_text(encoding="utf-8") or "[]")
    print(f"Modele : {MODEL} | {len(alertes)} alertes a classer")
    client = genai.Client(http_options={"timeout": 120_000})
    maintenant = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ids_attendus = {a["id_alerte"] for a in alertes}

    with SORTIE.open("w", encoding="utf-8") as out:
        for i in range(0, len(alertes), TAILLE_PAQUET):
            paquet = alertes[i:i + TAILLE_PAQUET]
            texte = "\n\n".join(
                f"[{a['id_alerte']}] {a['titre']}\n{a['resume_texte']}" for a in paquet
            )
            print(f"Paquet {i // TAILLE_PAQUET + 1} ({len(paquet)} alertes)...")
            for c in appeler(client, PROMPT.format(alertes=texte)):
                if str(c.get("id_alerte")) not in ids_attendus:
                    continue
                c["id_alerte"] = str(c["id_alerte"])
                c["modele"] = MODEL
                c["classe_le"] = maintenant
                out.write(json.dumps(c, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(3)
    print(f"Termine : {SORTIE}")


if __name__ == "__main__":
    main()
