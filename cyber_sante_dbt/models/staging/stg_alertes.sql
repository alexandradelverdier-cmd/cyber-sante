with source as (
    select
        cast(id_alerte as string)  as id_alerte,
        titre,
        lien,
        parse_timestamp('%a, %d %b %Y %H:%M:%S %z', date_publication) as publie_le,
        resume,
        cast(ingere_le as timestamp) as ingere_le
    from {{ source('cyber_sante', 'raw_alertes') }}
),

dedoublonne as (
    select *
    from source
    qualify row_number() over (partition by id_alerte order by ingere_le desc) = 1
)

select
    id_alerte,
    trim(split(titre, ' - ')[safe_offset(0)])          as editeur,
    regexp_extract(titre, r'CVE-\d{4}-\d+')            as cve_id,
    titre,
    publie_le,
    date(publie_le)                                    as date_publication,
    trim(regexp_replace(
        regexp_replace(resume, r'<[^>]+>', ' '), r'\s+', ' '
    ))                                                 as resume_texte,
    lien,
    ingere_le
from dedoublonne
