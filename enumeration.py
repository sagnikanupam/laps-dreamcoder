from utilities import eprint
from frontier import *
from task import *
from type import *
from program import *
from grammar import *

import gc

# def enumerateFrontiers(g, tasks, _=None,
#                        solver=None,
#                        frontierSize=None,
#                        enumerationTimeout=None,
#                        CPUs=1,
#                        maximumFrontier=None,
#                        verbose=True,
#                        evaluationTimeout=None):
#     '''g: Either a Grammar, or a map from task to grammar.'''
#     from time import time

#     solvers = {"ocaml": solveForTask_ocaml,
#                "pypy": enumerateForTask_pypy,
#                "python": enumerateForTask}
#     assert solver in solvers, \
#         "You must specify a valid solver. options are ocaml, pypy, or python."
#     solver = solvers[solver]

#     if not isinstance(g, dict): g = {t: g for t in tasks }

#     CPUsPerTask = 1 if len(tasks) > CPUs else int(float(CPUs)/len(tasks) + 0.5)
#     eprint("Allocating %d CPUs for each task"%CPUsPerTask)
#     if CPUsPerTask > 1 and solver is not solveForTask_ocaml:
#         eprint("(warning) Using more than one CPU for single task is currently only supported by ocaml.")
    
#     start = time()
#     frontiers = parallelMap(CPUs,
#                             lambda (task, grammar): solver(grammar, task,
#                                                            timeout=enumerationTimeout,
#                                                            CPUs=CPUsPerTask,
#                                                            evaluationTimeout = evaluationTimeout,
#                                                            maximumFrontier=maximumFrontier),
#                             map(lambda t: (t, g[t]), tasks),
#                             chunk = 1)
#     if verbose:
#         eprint("Enumerated %d frontiers in time %f"%(len(g), time() - start))

#     times = [t for f,t in frontiers if t is not None]
#     frontiers = [f for f,t in frontiers ]
#     return frontiers, times



def multithreadedEnumeration(g, tasks, _=None,
                             solver=None,
                             frontierSize=None,
                             enumerationTimeout=None,
                             CPUs=1,
                             maximumFrontier=None,
                             verbose=True,
                             evaluationTimeout=None):
    '''g: Either a Grammar, or a map from task to grammar.'''
    from time import time

    # We don't use actual threads but instead use the multiprocessing
    # library. This is because we need to be able to kill workers.
    from multiprocessing import Process, Queue

    assert frontierSize is None, "deprecated: frontierSize"

    solvers = {"ocaml": solveForTask_ocaml,
               "pypy": solveForTask_pypy,
               "python": solveForTask_python}
    assert solver in solvers, \
        "You must specify a valid solver. options are ocaml, pypy, or python."
    solver = solvers[solver]

    if not isinstance(g, dict): g = {t: g for t in tasks }
    task2grammar = g

    allowMultipleThreadsPerTask = CPUs > len(tasks)
    if allowMultipleThreadsPerTask:
        eprint("EXPERIMENTAL: Multiple processes will be working on a single task simultaneously.")

    frontiers = {t: Frontier([], task = t) for t in task2grammar }

    # Tasks which have not yet been solved
    activeTasks = set(task2grammar.keys())

    # Largest lower bound of any workerthat is assigned to a task
    lowerBounds = {t: 0. for t in task2grammar}

    # Map from task to the shortest time to find a program solving it
    bestSearchTime = {t: None for t in task2grammar}
    
    # For each task we keep track of how long we have been working on it
    stopwatches = {t: Stopwatch() for t in tasks }

    # Total number of evaluated programs
    totalExplored = 0

    # Each worker is assigned a unique ID number
    nextID = 0

    # If we kill a worker we also need to kill all of the processes at its spawned
    # Maps from ID to list of PIDs
    workerChildren = {}
    
    # map from ID to task
    workers = {}
    
    def budgetIncrement(lb):
        return 1.
        # if lb < 21.:
        #     return 1.
        # else:
        #     return 0.5

    startTime = time()

    # Workers put their messages in here
    q = Queue()

    while True:
        activeTasks = {t for t in activeTasks
                       if len(frontiers[t]) < maximumFrontier \
                       and stopwatches[t].elapsed <= enumerationTimeout }

        finished = len(activeTasks) == 0

        if not finished:
            while len(workers) < CPUs:
                # Sort the tasks by lower bound. Prioritize lower
                # lower bounds to explore shorter programs first
                for t in sorted(activeTasks, key = lambda t: lowerBounds[t])[:CPUs]:
                    thisTimeout = enumerationTimeout - stopwatches[t].elapsed
                    if not stopwatches[t].running: stopwatches[t].start()
                    eprint("Launching [%s] w/ lb = %f, timeout = %f"%(t,lowerBounds[t],thisTimeout))
                    bi = budgetIncrement(lowerBounds[t])
                    launchParallelProcess(wrapInThread(solver),
                                          q = q, ID = nextID,
                                          elapsedTime = stopwatches[t].elapsed,
                                          g = task2grammar[t],
                                          task = t,
                                          lowerBound = lowerBounds[t],
                                          upperBound = lowerBounds[t] + bi,
                                          budgetIncrement = bi,
                                          timeout = thisTimeout,
                                          evaluationTimeout = evaluationTimeout,
                                          maximumFrontier = maximumFrontier - len(frontiers[t]))
                    lowerBounds[t] += bi
                    workers[nextID] = t
                    nextID += 1

        if len(workers) > 0:
            message = Bunch(q.get())
            ID = message.ID
            if message.result == "fork":
                eprint("Got the message that worker",ID," forked child",message.child)
                workerChildren[ID] = workerChildren.get(ID,[])
                workerChildren[ID].append(message.child)
            elif message.result == "failure":
                eprint("PANIC! Exception in child worker:", message.exception)
                assert False
            elif message.result == "success":
                frontier, searchTime, explored = message.value
                task = workers[ID]

                totalExplored += explored
                if totalExplored > 0:
                    eprint("(python) Explored %d programs in %s sec. %d programs/sec."%
                           (totalExplored, int(time() - startTime), int(float(totalExplored)/(time() - startTime))))

                if searchTime is not None:
                    eprint("(python) Got first solution to %s after %s wall clock seconds"%(task,int(searchTime+0.5)))
                    if bestSearchTime[task] is None: bestSearchTime[task] = searchTime
                    else: bestSearchTime[task] = min(searchTime, bestSearchTime[task])
                frontiers[task] = frontiers[task].combine(frontier)

                # Remove the finished worker
                del workers[ID]

                if len(frontiers[task]) >= maximumFrontier:
                    # Forcibly terminate the workers
                    # FIXME in theory this creates a race condition wrt q
                    # We could end up trying to terminate the process that is busy writing to q
                    for pid in [ pid
                                 for i,t in workers.iteritems() if t == task
                                 for pid in workerChildren[i] ]:
                        os.system("kill -9 %s"%pid)                        
                        eprint("Forcibly terminated process that was related to task",task)
                    uselessIDs = { i for i,t in workers.iteritems() if t == task }
                    for i in uselessIDs: del workers[i]
                        
                # stop it stopwatch if the task is no longer being
                # worked on
                if not any( task == _task for _task in workers.values() ):
                    stopwatches[task].stop()

        if finished and len(workers) == 0 and q.empty(): break

    eprint("Completed multithreaded enumeration for",len(tasks),"tasks in",int(time() - startTime),"s")
    pps = float(totalExplored)/(time() - startTime)
    eprint("program evaluations per second:",int(pps))
    eprint("program evaluations per CPU second:",int(pps/CPUs))

    return [frontiers[t] for t in tasks], [bestSearchTime[t] for t in tasks if bestSearchTime[t] is not None ]

                    
            

    

def wrapInThread(f):
    """
    Returns a function that is designed to be run in a thread/threadlike process.
    Result will be either put into the q
    """
    
    def _f(*a,**k):
        q = k["q"]
        ID = k["ID"]
        assert q is not None
        assert ID is not None

        q.put({"result": "fork",
               "child": getPID(),
               "ID": ID})
        try:
            r = f(*a,**k)
            q.put({"result": "success",
                   "ID": ID,
                   "value": r})
        except Exception as e:
            q.put({"result": "failure",
                   "exception": e,
                   "ID": ID})
            return 
    return _f        

def solveForTask_ocaml(_ = None,
                       q = None, ID = None,
                       elapsedTime = 0.,
                       g = None, task = None,
                       lowerBound = None, upperBound = None, budgetIncrement = None,
                       timeout = None,
                       evaluationTimeout = None, maximumFrontier = None):
    import json
    message = {"DSL": {"logVariable": g.logVariable,
                       "productions": [ {"expression": str(p), "logProbability": l}
                                            for l,_,p in g.productions ]},
               "examples": [{"inputs": list(xs), "output": y} for xs,y in task.examples ],
               "programTimeout": evaluationTimeout,
               "solverTimeout": max(int(timeout + 0.5), 1),
               "maximumFrontier": maximumFrontier,
               "name": task.name,
               "lowerBound": lowerBound,
               "upperBound": upperBound,
               "budgetIncrement": budgetIncrement,
               "verbose": False}
    message = json.dumps(message)
    try:
        p = subprocess.Popen(['./solver'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if q is not None:
            assert ID is not None
            eprint("Sauber ID",ID, "has child",p.pid)
            q.put({"result": "fork",
                   "child": p.pid,
                   "ID": ID})
        try:
            response, error = p.communicate(message)
            response = json.loads(response)
        except Exception as exc:
            exc = ValueError("Could not load response from ocaml solver: ", exc)
            raise exc
    except OSError as exc:
        raise exc

    pc = response[u"programCount"]
    # Remove all entries that do not type correctly
    # This can occur because the solver tries to infer the type
    # Sometimes it infers a type that is too general
    response = [r for r in response[u"solutions"] if Program.parse(r["program"]).canHaveType(task.request) ]
    
    frontier = Frontier([FrontierEntry(program = p,
                                       logLikelihood = e["logLikelihood"],
                                       logPrior = g.logLikelihood(task.request, p))
                         for e in response
                         for p in [Program.parse(e["program"])] ],
                        task = task)

    if frontier.empty: searchTime = None
    else: searchTime = min(e["time"] for e in response) + elapsedTime

    return frontier, searchTime, pc

def solveForTask_pypy(_ = None,
                      q = None, ID = None,
                      elapsedTime = 0.,
                      g = None, task = None,
                      lowerBound = None, upperBound = None, budgetIncrement = None,
                      timeout = None,
                      evaluationTimeout = None, maximumFrontier = None):
    return callCompiled(enumerateForTask,
                        g,task,
                        timeout = timeout,
                        evaluationTimeout = evaluationTimeout,
                        maximumFrontier = maximumFrontier,
                        budgetIncrement = budgetIncrement,
                        lowerBound = lowerBound,
                        upperBound = upperBound,
                        PIDCallBack = lambda PID: q.put({"result": "fork",
                                                         "child": PID,
                                                         "ID": ID}))

def solveForTask_python(_ = None,
                        ID = None, q = None,
                        elapsedTime = 0.,
                        g = None, task = None,
                        lowerBound = None, upperBound = None, budgetIncrement = None,
                        timeout = None,
                        evaluationTimeout = None, maximumFrontier = None):
    return enumerateForTask(g,task,
                            timeout = timeout,
                            evaluationTimeout = evaluationTimeout,
                            maximumFrontier = maximumFrontier,
                            budgetIncrement = budgetIncrement,
                            lowerBound = lowerBound, upperBound = upperBound)

class EnumerationTimeout(Exception): pass
def enumerateForTask(g, task, _ = None,
                     verbose=False,
                     timeout=None,
                     evaluationTimeout=None,
                     frontierSize=None,
                     lowerBound = 0.,
                     upperBound = 100.,
                     budgetIncrement=1.0, maximumFrontier = 10**2):
    assert (timeout is not None) or (frontierSize is not None), \
        "enumerateForTask: You must provide either a timeout or a frontier size."
    
    from time import time

    timeUntilFirstSolution = None
    frontier = []
    starting = time()
    previousBudget = lowerBound
    budget = lowerBound + budgetIncrement
    try:
        totalNumberOfPrograms = 0
        while len(frontier) < maximumFrontier:
            numberOfPrograms = 0
            for prior,_,p in g.enumeration(Context.EMPTY, [], task.request, 
                                           maximumDepth = 99,
                                           upperBound = budget,
                                           lowerBound = previousBudget):
                descriptionLength = -prior
                # Shouldn't see it on this iteration
                assert descriptionLength <= budget
                # Should already have seen it
                assert descriptionLength > previousBudget

                numberOfPrograms += 1
                totalNumberOfPrograms += 1
                
                likelihood = task.logLikelihood(p, timeout=evaluationTimeout)
                if valid(likelihood):
                    if verbose:
                        eprint("Hit",task.name,"with the program",p,"which has prior",prior,"after",time() - starting,"seconds")
                    if frontier == []: timeUntilFirstSolution = time() - starting                        
                    frontier.append(FrontierEntry(program = p,
                                                  logPrior = prior,
                                                  logLikelihood = likelihood))

                if timeout is not None and time() - starting > timeout:
                    raise EnumerationTimeout
            if verbose:
                eprint("Enumerated %d programs of satisfying:"%(numberOfPrograms),
                       "%d < MDL <= %d."%(int(previousBudget),int(budget)))
            
            previousBudget = budget
            budget += budgetIncrement
            if verbose:
                eprint("\tTotal elapsed time: %d seconds. Total number of programs evaluated: %d. Task: %s."% \
                       (time() - starting, totalNumberOfPrograms, task))
            if frontierSize is not None and totalNumberOfPrograms > frontierSize: break
            if budget > upperBound: break
    except EnumerationTimeout:
        if verbose:
            eprint("Timeout triggered after",time() - starting,"seconds for task",task)

    frontier = Frontier(frontier,
                        task = task).topK(maximumFrontier)
    
    return frontier, timeUntilFirstSolution, numberOfPrograms

def solveSingleTask(grammar, task, maximumBudget = 15):
    if isinstance(task, DifferentiableTask):
        rememberOld = True
        history = set([])
    else: rememberOld = False
    for budget in range(2, maximumBudget):
        for _,_,p in grammar.enumeration(Context.EMPTY, [], task.request, budget):
            if rememberOld:
                if p in history: continue
                history.add(p)
            l = task.logLikelihood(p)
            if valid(l): return l,p
    return None

def benchmarkSynthesisTimes(result, tasks, _ = None, timeout = None, CPUs = None):
    if result.parameters['useRecognitionModel']:
        assert hasattr(result, 'recognitionModel') and result.recognitionModel is not None, \
            "Checkpoint was trained using a recognition model but it does not have a saved recognition model."

    times = parallelMap(CPUs, lambda task: benchmarkSynthesisTime(result, task, timeout), tasks)
    timeouts = sum(t == None for t in times)
    successes = sum(t != None for t in times)
    if successes > 0:
        average = sum(t[0] for t in times if t != None)/float(successes)
        deviation = (sum( (t[0] - average)**2 for t in times if t != None )/float(successes))**0.5
        standardError = deviation/(float(successes)**0.5)
    eprint("BENCHMARK:")
    eprint("Solves %d/%d = %d%%"%(successes, len(tasks), int(100.*successes/len(tasks))))
    if successes > 0:
        eprint("Synthesis time %f +/- %f sec"%(average, standardError))
        average = sum(t[1] for t in times if t != None)/float(successes)
        deviation = (sum( (t[1] - average)**2 for t in times if t != None )/float(successes))**0.5
        standardError = deviation/(float(successes)**0.5)
        eprint("Expected log P[t|p] =",average,"+/-",standardError)

def benchmarkSynthesisTime(result, task, timeout):
    grammar = result.grammars[-1]
    
    from time import time
    import signal
    
    startTime = time()
    if result.parameters['useRecognitionModel']:
        # Because grammar induction is the last step of EC, the
        # recognition model is actually trained for the second to last
        # grammar
        grammar = result.grammars[-2]        
        features = result.recognitionModel.featureExtractor.featuresOfTask(task)
        variables, productions = result.recognitionModel(features)
        grammar = Grammar(variables.data[0],
                          [ (productions.data[k],t,p)
                            for k,(_,t,p) in enumerate(grammar.productions) ])

    elapsed = time() - startTime
    frontier = callCompiled(enumerateForTask,
                            grammar, task,
                            maximumFrontier = 1,
                            timeout = timeout - elapsed)
    dt = time() - startTime
    if dt > timeout or len(frontier) == 0: return None
    l = solution.entries[0].logLikelihood
    p = solution.entries[0].program
    eprint("Solved",task,"w/",p,"(log likelihood of task given program:",l,").","in time",dt)
    return dt,l
    
