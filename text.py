from ec import explorationCompression, commandlineArguments, RegressionTask
from grammar import Grammar
from utilities import eprint, testTrainSplit
from makeTextTasks import makeTasks, delimiters
from textPrimitives import primitives

def stringFeatures(s):
    return [len(s)] + [sum(x == d for x in s ) for d in delimiters ] + [sum(x.upper() == x for x in s )]
def problemFeatures(task):
    inputFeatures = []
    outputFeatures = []
    for (x,),y in task.examples:
        inputFeatures.append(stringFeatures(x))
        outputFeatures.append(stringFeatures(y))
    n = float(len(task.examples))
    inputFeatures = map(lambda *a: sum(a)/n, *inputFeatures)
    outputFeatures = map(lambda *a: sum(a)/n, *outputFeatures)
    return inputFeatures + outputFeatures


if __name__ == "__main__":
    tasks = makeTasks()
    for t in tasks:
        t.features = problemFeatures(t)
    eprint("Generated",len(tasks),"tasks")

    test, train = testTrainSplit(tasks, 0.5)

    RegressionTask.standardizeFeatures(train)

    baseGrammar = Grammar.uniform(primitives)
    explorationCompression(baseGrammar, train,
                           outputPrefix = "experimentOutputs/text",
                           **commandlineArguments(
                               frontierSize = 10**4,
                               iterations = 10,
                               a = 2,
                               pseudoCounts = 10.0))
