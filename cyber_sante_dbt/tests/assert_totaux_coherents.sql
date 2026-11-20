-- Echoue si une ligne "total" porte une autre modalite que "total"
select annee, indicateur, modalite, valeur
from {{ ref('stg_indicateurs') }}
where dimension = 'total' and modalite != 'total'
