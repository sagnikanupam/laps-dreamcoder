from towerPrimitives import ttower

from task import *

import math


class TowerTask(Task):
    RESULTCASH = {}
    tasks = []
    STABILITYTHRESHOLD = 0.5
    
    def __init__(self, _ = None, perturbation = 0,
                 maximumMass = 100,
                 minimumLength = 0,
                 minimumArea = 0,
                 minimumHeight = None):
        name = "; ".join("%s: %s"%(k,v) for k,v in locals() .iteritems()
                         if not k in {"_","self"} )
        features = [perturbation,
                    float(maximumMass),
                    float(minimumHeight),
                    float(minimumLength),
                    float(minimumArea)]
        super(TowerTask, self).__init__(name, ttower, [],
                                        features = features)

        self.perturbation = perturbation
        self.minimumLength = minimumLength
        self.maximumMass = maximumMass
        self.minimumHeight = minimumHeight
        self.minimumArea = minimumArea

        TowerTask.tasks.append(self)

    @staticmethod
    def evaluateTower(tower, perturbation):
        from towers.tower_common import TowerWorld
        
        key = (tuple(tower), perturbation)
        if key in TowerTask.RESULTCASH: result = TowerTask.RESULTCASH[key]
        else:
            w = TowerWorld()
            # try:
            result = w.sampleStability(tower, perturbation, N = 30)
            # except Exception as exception:
            #     eprint("exception",exception)
            #     eprint(perturbation, tower)
            #     raise exception                
            
            TowerTask.RESULTCASH[key] = result
        return result

    def logLikelihood(self, e, timeout = None):
        tower = e.evaluate([])
        mass = sum(w*h for _,w,h in tower)
        if mass > self.maximumMass: return NEGATIVEINFINITY

        tower = centerTower(tower)

        result = TowerTask.evaluateTower(tower, self.perturbation)
        
        if result.height < self.minimumHeight:
            #eprint("height",result.height)
            return NEGATIVEINFINITY
        if result.stability < TowerTask.STABILITYTHRESHOLD:
            #eprint("stability")
            return NEGATIVEINFINITY
        if result.length < self.minimumLength:
            #eprint("len()", result.length)
            return NEGATIVEINFINITY
        if result.area < self.minimumArea:
            #eprint("area")
            return NEGATIVEINFINITY
        return 50.0*math.log(result.stability)

    def animateSolution(self, e):
        import os

        if isinstance(e, Program):
            tower = e.evaluate([])
        else:
            assert isinstance(e, list)
            tower = e

        os.system("python towers/visualize.py '%s' %f"%(tower, self.perturbation))

    def drawSolution(self,tower):
        from towers.tower_common import TowerWorld
        return TowerWorld().draw(tower)

def centerTower(t):
    x1 = max(x for x,_,_ in t )
    x0 = min(x for x,_,_ in t )
    c = float(x1 + x0)/2.
    return [ (x - c, w, h) for x,w,h in t ]
        
def makeTasks():
    STRONGPERTURBATION = 12
    MILDPERTURBATION = 8
    MASSES = [10,20,30]
    HEIGHT = [3,5,6]
    return [ TowerTask(maximumMass = float(m),
                       minimumArea = float(a),
                       perturbation = float(p),
                       minimumLength = float(l),
                       minimumHeight = float(h))
             for m in MASSES
             for a in [1, 2.9, 5.8]
             for l in [0, 5]
             for p in [MILDPERTURBATION, STRONGPERTURBATION]
             for h in HEIGHT
             if not ((p == STRONGPERTURBATION and m == min(MASSES)) or \
                     (p == STRONGPERTURBATION and h == max(HEIGHT)))
    ]


