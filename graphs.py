from ec import *
import dill
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plot
from matplotlib.ticker import MaxNLocator
import matplotlib.lines as mlines

import matplotlib
#from test_unpickle import loadfun
def loadfun(x):
    with open(x, 'rb') as handle:
        result = dill.load(handle)
    return result

TITLEFONTSIZE = 14
TICKFONTSIZE = 12
LABELFONTSIZE = 14

matplotlib.rc('xtick', labelsize=TICKFONTSIZE)
matplotlib.rc('ytick', labelsize=TICKFONTSIZE)


class Bunch(object):
    def __init__(self, d):
        self.__dict__.update(d)

    def __setitem__(self, key, item):
        self.__dict__[key] = item

    def __getitem__(self, key):
        return self.__dict__[key]


relu = 'relu'
tanh = 'tanh'
sigmoid = 'sigmoid'
DeepFeatureExtractor = 'DeepFeatureExtractor'
LearnedFeatureExtractor = 'LearnedFeatureExtractor'
TowerFeatureExtractor = 'TowerFeatureExtractor'

def averageCurves(curves):
    xs = {x
          for xs,_ in curves
          for x in xs }
    xs = list(sorted(list(xs)))
    curves = [{x:y for x,y in zip(xs,ys) }
              for xs,ys in curves ]
    ys = []
    for x in xs:
        y_ = []
        for curve in curves:
            if x in curve: y_.append(curve[x])
        ys.append(sum(y_)/len(y_))
    return xs,ys

def parseResultsPath(p):
    def maybe_eval(s):
        try:
            return eval(s)
        except BaseException:
            return s

    p = p[:p.rfind('.')]
    domain = p[p.rindex('/') + 1: p.index('_')]
    rest = p.split('_')[1:]
    if rest[-1] == "baselines":
        rest.pop()
    parameters = {ECResult.parameterOfAbbreviation(k): maybe_eval(v)
                  for binding in rest if '=' in binding
                  for [k, v] in [binding.split('=')]}
    parameters['domain'] = domain
    return Bunch(parameters)

def showSynergyMatrix(results):
    # For each result, compile the total set of tasks that are ever solved by that run
    everSolved = []
    for r in results:
        everSolved.append({ t.name for t,f in r.allFrontiers.items() if not f.empty })
        N = len(r.allFrontiers)

    print("Of the",len(results),"checkpoints that you gave me, here is a matrix showing the overlap between the tasks solved:")

    for y in range(len(results)):
        if y == 0: print("".join( f"\tck{i + 1}" for i in range(len(results)) ))
        for x in range(len(results)):
            if x == 0: print("ck%d"%(y+1),
                             end="\t")
            intersection = len(everSolved[x]&everSolved[y])
            improvementOverBaseline = intersection/N
            print(int(improvementOverBaseline*100 + 0.5),
                  end="%\t")
        print()

    if len(results) == 3:
        print("Here's the percentage of tasks that are uniquely solved by the first checkpoint:")
        print(int(len(everSolved[0] - everSolved[1] - everSolved[2])/len(everSolved[0])*100 + 0.5),
              end="%")
        print()
    

def plotECResult(
        resultPaths,
        interval=False,
        timePercentile=False,
        labels=None,
        failAsTimeout=False,
        title=None,
        testingTimeout=None,
        export=None,
        showSolveTime=True,
        showTraining=False,
        iterations=None,
        maxP=110,
        showEpochs=False,
        colors=None,
        epochFrequency=1,
        averageColors=False):
    results = []
    parameters = []
    for path in resultPaths:
        result = loadfun(path)
        print("loaded path:", path)

        if hasattr(result, "baselines") and result.baselines:
            assert False, "baselines are deprecated."
        else:
            results.append(result)
            parameters.append(parseResultsPath(path))

    if testingTimeout is not None:
        for r in results:
            r.testingSearchTime = [ [t for t in ts if t <= testingTimeout ]
                                    for ts in r.testingSearchTime ]
    
    f, a1 = plot.subplots(figsize=(4, 3))
    a1.set_xlabel("Wake/Sleep Cycles", fontsize=LABELFONTSIZE)
    a1.xaxis.set_major_locator(MaxNLocator(integer=True))

    a1.set_ylabel('%% %s Solved%s'%("Training" if showTraining else "Test",
                                    " (solid)" if showSolveTime else ""),
                  fontsize=LABELFONTSIZE)
    if showSolveTime:
        a2 = a1.twinx()
        a2.set_ylabel('Solve time (dashed)', fontsize=LABELFONTSIZE)

    n_iters = max(len(result.learningCurve) for result in results)
    if iterations and n_iters > iterations:
        n_iters = iterations

    plot.xticks(range(0, n_iters), fontsize=TICKFONTSIZE)

    if colors is None:
        assert not averageColors, "If you are averaging the results from checkpoints with the same color, then you need to tell me what colors the checkpoints should be. Try passing --colors ..."
        colors = ["#D95F02", "#1B9E77", "#662077", "#FF0000"] + ["#000000"]*100
    usedLabels = []

    showSynergyMatrix(results)

    cyclesPerEpic = None
    plotCommands = {} # Map from (color,line style) to (xs,ys)
    for result, p, color in zip(results, parameters, colors):
        if showTraining:
            ys = [100.*t/float(len(result.taskSolutions))
                  for t in result.learningCurve[:iterations]]
        else:
            ys = [100. * len(t) / result.numTestingTasks
                  for t in result.testingSearchTime[:iterations]]
            
        xs = list(range(0, len(ys)))
        if showEpochs:
            if 'taskBatchSize' not in p.__dict__:
                print("warning: Could not find batch size in result. Assuming batching was not used.")
                newCyclesPerEpic = 1
            else:
                newCyclesPerEpic = (float(len(result.taskSolutions))) / p.taskBatchSize
            if cyclesPerEpic is not None and newCyclesPerEpic != cyclesPerEpic:
                print("You are asking to show epochs, but the checkpoints differ in terms of how many w/s cycles there are per epochs. aborting!")
                assert False
            cyclesPerEpic = newCyclesPerEpic
        if labels:
            usedLabels.append((labels[0], color))
            labels = labels[1:]

        plotCommands[(color,'-')] = plotCommands.get((color,'-'),[]) + [(xs,ys)]
        
        if showSolveTime:
            if failAsTimeout:
                assert testingTimeout is not None
                result.testingSearchTime = [ ts + [testingTimeout]*(result.numTestingTasks - len(ts))
                                             for ts in result.testingSearchTime ]
                result.searchTimes = [ ts + [p.enumerationTimeout]*(len(result.taskSolutions) - len(ts))
                                       for ts in result.searchTimes ]

            if not showTraining: times = result.testingSearchTime[:iterations]
            else: times = result.searchTimes[:iterations]
            a2.plot(xs,
                    [mean(ts) if not timePercentile else median(ts)
                         for ts in times],
                    color=color, ls='--')
            if interval and result is results[0]:
                a2.fill_between(xs,
                                [percentile(ts, 0.75) if timePercentile else mean(ts) + standardDeviation(ts)
                                 for ts in times],
                                [percentile(ts, 0.25) if timePercentile else mean(ts) - standardDeviation(ts)
                                 for ts in times],
                                facecolor=color, alpha=0.2)

    if averageColors:
        plotCommands = {kl: averageCurves(curves)
                        for kl, curves in plotCommands.items() }
    for (color,ls),(xs,ys) in plotCommands:
        a1.plot(xs,ys,color=color,ls=ls)

    a1.set_ylim(ymin=0, ymax=maxP)
    a1.yaxis.grid()
    a1.set_yticks(range(0, maxP, 20))
    plot.yticks(range(0, maxP, 20), fontsize=TICKFONTSIZE)

    cycle_label_frequency = 1
    if n_iters >= 10: cycle_label_frequency = 2
    if n_iters >= 20: cycle_label_frequency = 5
    for n, label in enumerate(a1.xaxis.get_ticklabels()):
        if n%cycle_label_frequency != 0:
            label.set_visible(False)

    if showEpochs:
        nextEpicLabel = 1
        while nextEpicLabel*cyclesPerEpic <= n_iters:
            a1.annotate('Epoch %d'%nextEpicLabel if (nextEpicLabel - 1)%epochFrequency == 0 else " ",
                        xy=(nextEpicLabel*cyclesPerEpic, 0),
                        xytext=(nextEpicLabel*cyclesPerEpic, 20),
                        arrowprops=dict(facecolor='black', shrink=0.05),
                        horizontalalignment='center')
            nextEpicLabel += 1
            

    if showSolveTime:
        a2.set_ylim(ymin=0)
        starting, ending = a2.get_ylim()
        ending10 = 10*int(ending/10 + 1)
        a2.yaxis.set_ticks([ int(ending10/6)*j
                             for j in range(0, 6)]) 
        for tick in a2.yaxis.get_ticklabels():
            tick.set_fontsize(TICKFONTSIZE)

    if title is not None:
        plot.title(title, fontsize=TITLEFONTSIZE)

    if labels is not None:
        a1.legend(loc='lower right', fontsize=9,
                  handles=[mlines.Line2D([], [], color=color, ls='-',
                                         label=label)
                           for label, color in usedLabels])
    f.tight_layout()
    if export:
        plot.savefig(export)
        eprint("Exported figure ",export)
        if export.endswith('.png'):
            os.system('convert -trim %s %s' % (export, export))
        os.system('feh %s' % export)
    else:
        f.show()
        

if __name__ == "__main__":
    import sys

    import argparse
    parser = argparse.ArgumentParser(description = "")
    parser.add_argument("--checkpoints",nargs='+')
    parser.add_argument("--colors",nargs='+')
    parser.add_argument("--title","-t",type=str,
                        default="")
    parser.add_argument("--iterations","-i",
                        type=int, default=None,
                        help="number of iterations/epochs of EC to show. If combined with --showEpochs this will bound the number of epochs.")
    parser.add_argument("--names","-n",
                        type=str, default="",
                        help="comma-separated list of names to put on the plot for each checkpoint")
    parser.add_argument("--export","-e",
                        type=str, default=None)
    parser.add_argument("--percentile","-p",
                        default=False, action="store_true",
                        help="When displaying error bars for synthesis times, this option will cause it to show 25%/75% interval. By default it instead shows +/-1 stddev")
    parser.add_argument("--interval",
                        default=False, action="store_true",
                        help="Should we show error bars for synthesis times?")
    parser.add_argument("--testingTimeout",
                        default=None, type=float,
                        help="Retroactively pretend that the testing timeout was something else. WARNING: This will only give valid results if you are retroactively pretending that the testing timeout was smaller than it actually was!!!")
    parser.add_argument("--failAsTimeout",
                        default=False, action="store_true",
                        help="When calculating average solve time, should you count missed tasks as timeout OR should you just ignore them? Default: ignore them.")
    parser.add_argument("--showTraining",
                        default=False, action="store_true",
                        help="Graph results for training tasks. By default only shows results for testing tasks.")
    parser.add_argument("--maxPercent","-m",
                        type=int, default=110,
                        help="Maximum percent for the percent hits graph")
    parser.add_argument("--showEpochs",
                        default=False, action="store_true",
                        help='X-axis is real-valued percentage of training tasks seen, instead of iterations.')
    parser.add_argument("--noTime",
                        default=False, action="store_true",
                        help='Do not show solve time.')
    parser.add_argument("--epochFrequency",
                        default=1, type=int,
                        help="Frequency with which to show epoch markers.")
    parser.add_argument("--averageColors",
                        default=False, action="store_true",
                        help="If multiple curves are assigned the same color, then we will average them")
    
    arguments = parser.parse_args()
    
    plotECResult(arguments.checkpoints,
                 testingTimeout=arguments.testingTimeout,
                 timePercentile=arguments.percentile,
                 export=arguments.export,
                 title=arguments.title,
                 failAsTimeout=arguments.failAsTimeout,
                 labels=arguments.names.split(",") if arguments.names != "" else None,
                 interval=arguments.interval,
                 iterations=arguments.iterations,
                 showTraining=arguments.showTraining,
                 maxP=arguments.maxPercent,
                 showSolveTime=not arguments.noTime,
                 showEpochs=arguments.showEpochs,
                 epochFrequency=arguments.epochFrequency,
                 colors=arguments.colors,
                 averageColors=arguments.averageColors)
