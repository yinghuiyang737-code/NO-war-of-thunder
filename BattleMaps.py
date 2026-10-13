"""Battle layouts, selected independently for each new battle."""
import random
MAPS={
 'wilderness':{'name':'钢铁旷野','seed':7182,'points':(('A',(4500,3500)),)},
 'three_fronts':{'name':'秋季三线林地','seed':29147,'points':(('A',(4500,1500)),('B',(4500,3500)),('C',(4500,5500)))},
 'urban_front':{'name':'冬季城郊交锋','seed':60439,'points':(('A',(3600,2400)),('B',(4500,3500)),('C',(5400,4800)))},
}
def choose_map(rng=None):return (rng or random).choice(tuple(MAPS))
