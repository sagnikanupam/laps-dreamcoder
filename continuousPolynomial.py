from ec import explorationCompression, commandlineArguments, Program
from grammar import Grammar
from arithmeticPrimitives import addition, multiplication, real
from task import DifferentiableTask, squaredErrorLoss, l1loss, RegressionTask
from type import tint, arrow
from utilities import *

primitives = [addition, multiplication, real]

MAXIMUMCOEFFICIENT = 9
NUMBEROFEXAMPLES = 3
EXAMPLES = range(-(NUMBEROFEXAMPLES/2),
                 (NUMBEROFEXAMPLES - NUMBEROFEXAMPLES/2))
tasks = [ DifferentiableTask("%dx^2 + %dx + %d"%(a,b,c),
                             arrow(tint,tint),
                             [((x,),a*x*x + b*x + c) for x in EXAMPLES ],
                             loss = squaredErrorLoss,
                             features = [float(a*x*x + b*x + c) for x in EXAMPLES ],
                             likelihoodThreshold = -0.1)
          for a in range(MAXIMUMCOEFFICIENT+1)
          for b in range(MAXIMUMCOEFFICIENT+1)
          for c in range(MAXIMUMCOEFFICIENT+1) ]

if __name__ == "__main__":
    baseGrammar = Grammar.uniform(primitives)
    RegressionTask.standardizeFeatures(tasks)
    
    explorationCompression(baseGrammar, tasks,
                           outputPrefix = "experimentOutputs/continuousPolynomial",
                           **commandlineArguments(frontierSize = 10**2,
                                                  iterations = 5,
                                                  pseudoCounts = 10.0))
