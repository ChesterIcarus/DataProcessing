select distinct
    mazparcels.apn as apn,
    mazparcels.maz as maz
from network.mazparcels
inner join network.mazs
using(maz)
where mbrcontains(mazs.region, mazparcels.center) = 0
limit 20;