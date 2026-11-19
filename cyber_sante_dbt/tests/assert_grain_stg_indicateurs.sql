-- Echoue si un meme chiffre apparait plusieurs fois
select annee, indicateur, dimension, modalite, unite, count(*) as nb
from {{ ref('stg_indicateurs') }}
group by 1, 2, 3, 4, 5
having count(*) > 1
