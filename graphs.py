from ec import *

import numpy as np

import matplotlib.pyplot as plot
from matplotlib.ticker import MaxNLocator

class Bunch(object):
    def __init__(self,d):
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

def parseResultsPath(p):
    p = p[:p.rfind('.')]
    domain = p[p.rindex('/')+1 : p.index('_')]
    rest = p.split('_')[1:]
    if rest[-1] == "baselines":
        rest.pop()
    parameters = { ECResult.parameterOfAbbreviation(k): eval(v)
                   for binding in rest
                   for [k,v] in [binding.split('=')] }
    parameters['domain'] = domain
    return Bunch(parameters)

def PCAembedding(e,g):
    primitives = e.keys()
    matrix = np.array([ e[p] for p in primitives ])
    N,D = matrix.shape

    from sklearn.decomposition import PCA
    from sklearn.preprocessing import scale

    matrix = scale(matrix)
    solver = PCA(n_components = 2)
    matrix = solver.fit_transform(matrix)

    e = dict({p: matrix[j,:]
              for j,p in enumerate(primitives) })
    vectors = e.values()
    plot.scatter([ v[0] for v in vectors ],
                 [ v[1] for v in vectors ])
    best = [ p
             for l,t,p in sorted(g.productions, reverse = True)
             if p.isInvented or p.isPrimitive ][:10]
    for p,v in e.iteritems():
        if p in best:
            eprint(p)
            plot.annotate(prettyProgram(p),
                          (v[0] + random.random(),
                           v[1] + random.random()))

def plotECResult(resultPaths, colors='rgbycm', label=None, title=None, export=None):
    results = []
    parameters = []
    for j,path in enumerate(resultPaths):
        with open(path,'rb') as handle:
            result = pickle.load(handle)
            if hasattr(result, "baselines") and result.baselines:
                for name, res in result.baselines.iteritems():
                    results.append(res)
                    p = parseResultsPath(path)
                    p["baseline"] = name.replace("_", " ")
                    parameters.append(p)
            else:
                results.append(result)
                p = parseResultsPath(path)
                parameters.append(p)

    f,a1 = plot.subplots(figsize = (5,4))
    a1.set_xlabel('Iteration')
    a1.xaxis.set_major_locator(MaxNLocator(integer = True))
    a1.set_ylabel('% Hit Tasks (solid)')
    a2 = a1.twinx()
    a2.set_ylabel('Avg log likelihood (dashed)')

    n_iters = max(len(result.learningCurve) for result in results)

    for color, result, p in zip(colors, results, parameters):
        if hasattr(p, "baseline") and p.baseline:
            ys = [ 100. * result.learningCurve[-1] / len(result.taskSolutions) ]*n_iters
        else:
            ys = [ 100. * x / len(result.taskSolutions) for x in result.learningCurve]
        l, = a1.plot(range(1, len(ys) + 1), ys, color + '-')
        if label is not None:
            l.set_label(label(p))

        a2.plot(range(1,len(result.averageDescriptionLength) + 1),
                [ -l for l in result.averageDescriptionLength],
                color + '--')

    a1.set_ylim(ymin = 0, ymax = 110)
    a1.yaxis.grid()
    a1.set_yticks(range(0,110,10))
    #a2.set_ylim(ymax = 0)

    if title is not None:
        plot.title(title)

    if label is not None:
        a1.legend(loc = 'lower right', fontsize = 9)

    f.tight_layout()
    if export:
        plot.savefig(export)
        if export.endswith('.png'):
            os.system('convert -trim %s %s'%(export, export))
        os.system('feh %s'%export)
    else: plot.show()

    for result in results:
        if hasattr(result, 'embedding') and result.embedding is not None:
            plot.figure()
            PCAembedding(result.embedding, result.grammars[-1])
            if export:
                export = export[:-4] + "_embedding" + export[-4:]
                plot.savefig(export)
                os.system("feh %s"%(export))
            else: plot.show()


if __name__ == "__main__":
    import sys
    def label(p):
        #l = p.domain
        l = ""
        if hasattr(p, 'baseline') and p.baseline:
            l += " (baseline %s)"%p.baseline
            return l
        l += "frontier size %s"%p.frontierSize
        if p.useRecognitionModel:
            if hasattr(p,'helmholtzRatio') and p.helmholtzRatio > 0:
                l += " (neural Helmholtz)"
            else:
                l += " (neural)"
        return l
    arguments = sys.argv[1:]
    export = [ a for a in arguments if a.endswith('.png') or a.endswith('.eps') ]
    export = export[0] if export else None
    title = [ a for a in arguments if not any(a.endswith(s) for s in {'.eps', '.png', '.pickle'})  ]
    plotECResult([ a for a in arguments if a.endswith('.pickle') ],
                 export = export,
                 title = title[0] if title else "DSL learning curves",
                 label = label)
