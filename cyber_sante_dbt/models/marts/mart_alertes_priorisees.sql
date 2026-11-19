with classification as (
    select *
    from {{ source('cyber_sante', 'raw_classifications') }}
    qualify row_number() over (partition by id_alerte order by classe_le desc) = 1
),

details as (
    select *
    from {{ source('cyber_sante', 'raw_details_alertes') }}
    qualify row_number() over (partition by id_alerte order by recupere_le desc) = 1
),

assemble as (
    select
        a.id_alerte,
        a.date_publication,
        a.editeur,
        a.cve_id,
        a.titre,
        d.cvss,
        case
            when d.cvss >= 9 then 'critique'
            when d.cvss >= 7 then 'haute'
            when d.cvss >= 4 then 'moyenne'
            when d.cvss > 0  then 'faible'
        end                                  as gravite,
        c.gravite                            as gravite_llm,
        lower(d.exploitee)                   as exploitee,
        lower(d.correctif)                   as correctif,
        d.poc_disponible,
        d.cwe,
        d.vecteur,
        d.privileges,
        c.type_faille,
        c.categorie_si,
        c.pertinence_hopital,
        c.justification,
        a.lien
    from {{ ref('stg_alertes') }} a
    inner join classification c using (id_alerte)
    left join details d using (id_alerte)
)

select
    *,
    case pertinence_hopital when 'haute' then 3 when 'moyenne' then 2 else 1 end
    * case gravite when 'critique' then 4 when 'haute' then 3 when 'moyenne' then 2 else 1 end
    + if(exploitee = 'oui', 5, 0)
    + if(poc_disponible, 2, 0)
    + if(correctif = 'non', 2, 0)            as score_priorite
from assemble
