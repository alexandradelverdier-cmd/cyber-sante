with extrait as (
    select
        cast(annee as int64)          as annee,
        cast(annee_rapport as int64)  as annee_rapport,
        lower(trim(indicateur))       as indicateur,
        lower(trim(dimension))        as dimension,
        lower(trim(modalite))         as modalite,
        cast(valeur as float64)       as valeur,
        unite,
        cast(page as int64)           as page,
        extrait,
        'extraction_llm'              as origine_donnee
    from {{ source('cyber_sante', 'raw_indicateurs') }}
),

saisie as (
    select
        annee,
        cast(null as int64)           as annee_rapport,
        indicateur,
        dimension,
        modalite,
        cast(valeur as float64)       as valeur,
        unite,
        cast(null as int64)           as page,
        source                        as extrait,
        'saisie_manuelle'             as origine_donnee
    from {{ ref('saisie_manuelle') }}
),

dedoublonne as (
    select *
    from (select * from extrait union all select * from saisie)
    qualify row_number() over (
        partition by annee, indicateur, dimension, modalite, unite
        order by
            case origine_donnee when 'extraction_llm' then 1 else 2 end,
            if(annee_rapport = annee, 0, 1),
            annee_rapport desc
    ) = 1
)

select
    d.annee,
    d.indicateur,
    d.dimension,
    d.modalite,
    d.unite,
    coalesce(c.valeur_corrigee, d.valeur) as valeur,
    d.valeur                              as valeur_extraite,
    c.valeur_corrigee is not null         as est_corrige,
    c.source_correction,
    d.origine_donnee,
    d.annee_rapport,
    d.page,
    d.extrait
from dedoublonne d
left join {{ ref('corrections_manuelles') }} c
    using (annee, indicateur, dimension, modalite)
