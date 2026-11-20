#!/bin/zsh
set -e
P="alexandra-delverdier-perso.cyber_sante"

echo "1/6 Recuperation du flux RSS"
python ingest_alertes.py
bq load --source_format=NEWLINE_DELIMITED_JSON --autodetect $P.raw_alertes alertes_rss.jsonl
(cd cyber_sante_dbt && dbt run --select stg_alertes)

echo "2/6 Enrichissement CVSS des nouvelles alertes"
bq query --use_legacy_sql=false --format=json --max_rows=10000 "
SELECT a.id_alerte, a.lien FROM \`$P.stg_alertes\` a
LEFT JOIN \`$P.raw_details_alertes\` d USING (id_alerte)
WHERE d.id_alerte IS NULL" > a_enrichir.json
python enrichir_alertes.py
bq load --source_format=NEWLINE_DELIMITED_JSON $P.raw_details_alertes details_alertes.jsonl

echo "3/6 Classification des nouvelles alertes"
bq query --use_legacy_sql=false --format=json --max_rows=10000 "
SELECT a.id_alerte, a.titre, a.resume_texte FROM \`$P.stg_alertes\` a
LEFT JOIN \`$P.raw_classifications\` c USING (id_alerte)
WHERE c.id_alerte IS NULL" > a_classer.json
python classer_alertes.py
bq load --source_format=NEWLINE_DELIMITED_JSON $P.raw_classifications classifications.jsonl

echo "4/6 Construction et tests dbt"
(cd cyber_sante_dbt && dbt build)

echo "5/6 Export des alertes de la semaine"
bq query --use_legacy_sql=false --format=json --max_rows=1000 "
SELECT date_publication, editeur, cve_id, titre, cvss, gravite, exploitee,
       poc_disponible, correctif, categorie_si, pertinence_hopital,
       justification, score_priorite, lien
FROM \`$P.mart_alertes_priorisees\`
WHERE date_publication >= date_sub((SELECT max(date_publication) FROM \`$P.mart_alertes_priorisees\`), INTERVAL 6 DAY)
ORDER BY score_priorite DESC" > alertes_semaine.json

echo "6/6 Redaction de la note hebdomadaire"
python synthese_hebdo.py
