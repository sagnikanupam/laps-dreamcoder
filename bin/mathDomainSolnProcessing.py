import pandas as pd

import binutil
import dreamcoder.domains.mathDomain.mathDomainPrimitives as mdp
import mathDomainPrefixConversion as mdpc
from collections import OrderedDict 
import random

functions_dict = {
    '(_swap': mdp._swap, 
    '(_add': mdp._add, 
    '(_sub': mdp._sub, 
    '(_mult': mdp._mult, 
    '(_div': mdp._div, 
    '(_rrotate': mdp._rrotate, 
    '(_lrotate': mdp._lrotate, 
    '(_simplify': mdp._simplify, 
    '(_dist': mdp._dist, 
}

def replacements(s):
    """
    Given a string of a program generated by DreamCoder, replaces all mathDomain primitive names with their corresponding functions_dict index name.

    Inputs: 
        - s is is a string containing a lambda expression describing a program generated by DreamCoder which is a series of functions composed of primitives. E.g. - (lambda (#(lambda (mathDomain_simplify (mathDomain_dist $0 1) 0)) $0)) 
    
    Returns:
        - a string with all the mathDomain primitive names replaced. This output shall henceforth be referred to as a solution program expression.

    """
    replacements_dict = {'mathDomain_swap': '_swap', 'mathDomain_add': '_add', 'mathDomain_sub': '_sub', 'mathDomain_mult': '_mult', 'mathDomain_div': '_div', 'mathDomain_rrotate': '_rrotate', 'mathDomain_lrotate': '_lrotate', 'mathDomain_simplify': '_simplify', 'mathDomain_dist':'_dist'}
    for i in range(10):
        replacements_dict['mathDomain_'+str(i)] = str(i)
    for or_text in replacements_dict.keys():
        s = s.replace(or_text, replacements_dict[or_text])
    return s

def dsSolnFormat(dsSolnPath, eqnPath, outputSolnPath):
    '''
    Given a .csv file containing solution program expressions copied from the terminal output of DreamSolver, pass the expressions through replacements() and modify the expressions to make them more readable.
    
    Inputs:
        - dsSolnPath is a string containing a path to the .csv file containing the DreamSolver solution e.g.'bin/tempLargeDatasetSolns_1.csv'
        - outputSolnPath is a string containing a path to the .csv where we would like to store our modified DreamSolver solutions

    Returns:
        - None
    '''

    df = pd.read_csv(dsSolnPath)
    df_eq = pd.read_csv(eqnPath)
    equation_numbering_list = []
    reconstructed_solution_list = []
    solved_eq_list = []
    solved_eq_output_list = []
    

    for i in range(df.shape[0]):
        or_eq = df.loc[i]['output']
        or_eq_split = or_eq.split(' ')
        if or_eq_split[0]!="MISS":
            if or_eq_split[1][0:2]!="tr":
                eqn_no = or_eq_split[1][2:]
                solved_eq_list.append(str(df_eq.iat[int(eqn_no), 2]))
                solved_eq_output_list.append(or_eq)
                equation_numbering_list.append(eqn_no)
                reconstructed_solution_list.append(replacements(or_eq[or_eq.find('(') : or_eq.rfind(')')+1]))
    df_new = pd.DataFrame()
    df_new['output'] = solved_eq_output_list
    df_new['equation_number'] = equation_numbering_list
    df_new['eqn'] = solved_eq_list
    df_new['soln'] = reconstructed_solution_list
    print(df_new)

    df_new.to_csv(outputSolnPath)

def matchBr(s, ind):
    """
    Given an opening bracket at position ind in string s, find the  position of the corresponding closing bracket.

    Inputs: 
    - s is a string denoting the solution program expression (already processed by replacements())
    - ind is an integer denoting the starting position of the start bracket '('

    Returns: 
    - an integer denoting position of closing bracket. If start index does not have an open bracket or no closing brackets close the starting bracket, returns None.
    """
    brPair = 0
    for j in range(ind, len(s)):
        if s[j]=="(":
            brPair+=1
        if s[j]==")":
            brPair-=1
        if brPair==0:
            if j==ind:
                return None
            return j
    return None

def evaluate(s, arg, depth):
    """
    Given a solution program expression, generate mathematical solutions as a list of prefix expressions, stored as a string separated by |.

    Inputs: 
        - s is a string denoting the solution program expression (already processed by replacements())
        - arg is a string containing an equation as a prefix-tree expression. This is the equation to be solved.
        - depth is a parameter to modulate granularity of solutions, only functions with #lambdas<depth have the results of their argument included in the solution

    Returns:
        - a list comprising of all the steps of the DreamCoder solution i.e. all the steps we generate after evaluating abstractions 
    """

    init_split = s.split(" ")
    if s=="":
        return [arg]
    if arg=="":
        return [s]
    if init_split[0]=="$0":
        return [arg]
    if init_split[0].isnumeric():
        return [int(init_split[0])]
    if init_split[0]=="(lambda" or init_split[0]=="(#(lambda":
        subExpStart = 8 if init_split[0]=="(lambda" else 2
        subExpEnd = -1
        funcEnd = matchBr(s, subExpStart)
        if funcEnd!=None: 
            argEnd =  matchBr(s, funcEnd+2)
            if argEnd!=None:
                newFunc = s[subExpStart:funcEnd+1]
                newArgFunc = s[funcEnd+2:argEnd+1]
                #print("New Func is: "+newFunc)
                #print("New ArgFunc is: "+newArgFunc)
                #print("Currently, func is: "+s)
                #print("Currently, arg is: "+arg+"\n")
                evalArg = evaluate(newArgFunc, arg, depth+1)
                #print("Evaluated argument of " +s+" and " +arg + " is " +evalArg)
                if depth<5:
                    return evalArg+evaluate(newFunc, evalArg[-1], depth+1) #evalArg is appended as it is an output produced by an abstraction
                else:
                    return evaluate(newFunc, evalArg[-1], depth+1) 
            else:
                newFunc = s[subExpStart:funcEnd+1]
                newArgFunc = s[funcEnd+2:subExpEnd]
                #print("New Func is: "+newFunc)
                #print("New ArgFunc is: "+newArgFunc)
                #print("Currently, func is: "+s)
                #print("Currently, arg is: "+arg+"\n")
                evalArg = evaluate(newArgFunc, arg, depth+1)
                #print("Evaluated argument of " +s+" and " +arg + " is " +evalArg)
                return evaluate(newFunc, evalArg[-1], depth+1) #evalArg is not appended as it is simply a substring
        else:
            newFunc = s[subExpStart:-1]
            print("New Func is: "+newFunc)
            return evaluate(newFunc, arg, depth+1)
    
    if init_split[0] in functions_dict.keys():
        if init_split[1][0]=="(":
            arg1Start = len(init_split[0])+1
            arg1End = matchBr(s, arg1Start)
            arg2Start = arg1End + 2
            arg2End = -1
            if s[arg2Start]=="(":
                arg2End = matchBr(s, arg2Start)
            newArg1 = s[arg1Start:arg1End+1]
            newArg2 = s[arg1End+2:arg2End]
            #print("New Arg1 is: "+newArg1)
            #print("New Arg2 is: "+newArg2)
            #print("Currently, func is: "+s)
            #print("Currently, arg is: "+arg+"\n")
            evalNewArg1 = evaluate(newArg1, arg, depth+1)
            evalNewArg2 = evaluate(newArg2, arg, depth+1)
            #print("Evaluation: "+ s + " and " + arg + " result in " + str(evalNewArg1[-1]) + " and " + str(evalNewArg2[-1]))
            #return evalNewArg1 + [functions_dict[init_split[0]](evalNewArg1[-1], evalNewArg2[-1])] #evalNewArg1 is appended as it is an output produced by an abstraction
            return [functions_dict[init_split[0]](evalNewArg1[-1], evalNewArg2[-1])]
        else:
            newArg1 = init_split[1]
            newArg2 = init_split[2][:-1]
            if (init_split[2][0]=="("):
                arg2Start = len(init_split[0])+len(init_split[1])+2
                newArg2 = s[arg2Start:matchBr(arg2Start)+1]
            #print("New Arg1 is: "+newArg1)
            #print("New Arg2 is: "+newArg2)
            #print("Currently, func is: "+s)
            #print("Currently, arg is: "+arg+"\n")
            evalNewArg1 = evaluate(newArg1, arg, depth+1)
            evalNewArg2 = evaluate(newArg2, arg, depth+1)
            #print("Evaluation: "+ s + " and " + arg + " result in " + str(evalNewArg1[-1]) + " and " + str(evalNewArg2[-1]))
            return [functions_dict[init_split[0]](evalNewArg1[-1], evalNewArg2[-1])] #evalNewArg1 is not appended as it is simply a substring
    return [s]

def computeMetrics(steps):
    """
    Takes a list of solution steps (in prefix format) as input and computes their conciseness metric function value, f(s)

    Inputs:
        - steps is a list of strings containing equations in prefix format, which can be accepted by mdp.treefy()

    Returns:
        - an integer denoting the total value of the metric function for that equation
    """
    total_metric = 0
    for ind in range(1, len(steps)):
        total_metric+=mdp._metric(steps[ind-1],steps[ind])
    return total_metric

def clSolnEval(clSolnPath, outputSolnPath):
    '''
    Given a .csv file containing solutions generated by ConPoLe or Lemma, convert the solutions into lists of steps in prefix notation, and then compute each solution's metric function.
    
    Inputs:
        - clSolnPath is a string containing a path to the .csv file containing the ConPoLe/Lemma solutions e.g.'bin/tempLargeDatasetSolns_1.csv'
        - outputSolnPath is a string containing a path to the .csv where we would like to store our ConPoLe/Lemma solutions alongside their metric function values.
    
    Returns:
        - None
    '''
    df = pd.read_csv(clSolnPath)
    metrics = []
    for i in range(df.shape[0]):
        str_soln = df.loc[i]['soln']
        str_soln = str_soln.replace("[", "(")
        str_soln = str_soln.replace("]", ")")
        str_eq = df.loc[i]['eqn']
        steps = str_soln.split('|')
        steps = [str_eq]+steps
        prefix_steps = [mdpc.infix_to_prefix_conversion(step) for step in steps]
        metrics.append(computeMetrics(prefix_steps))
    df['metrics'] = metrics
    df.to_csv(outputSolnPath)

def dsSolnEval(dsSolnPath, outputSolnPath):
    '''
    Given a .csv file containing solution program expressions generated by DreamSolver and passed through replacement(), generate solutions from the expression, convert the solutions into lists of steps in prefix notation, and then compute each solution's metric function.
    
    Inputs:
        - dsSolnPath is a string containing a path to the .csv file containing the DreamSolver solution program expressions e.g.'bin/tempLargeDatasetSolns_1.csv'
        - outputSolnPath is a string containing a path to the .csv where we would like to store our DreamSolver solutions alongside their metric function values.
    
    Returns:
        - None
    '''
    df = pd.read_csv(dsSolnPath)
    metrics = []
    steps = []
    error_count = 0
    for i in range(df.shape[0]):
        try:
            str_soln = df.loc[i]['soln']
            str_eq = df.loc[i]['eqn']
            prefix_steps = evaluate(str_soln, str_eq, 0) # list(OrderedDict.fromkeys(evaluate(str_soln, str_eq, 0)))
            prefix_steps = [str_eq]+prefix_steps
            steps.append('|'.join(prefix_steps))
            metrics.append(computeMetrics(prefix_steps))
        except:
            error_count+=1
            print("Equation: ")
            print(df.loc[i]['eqn'])
            print("Solution: ")
            print(df.loc[i]['soln'])
            print("Prefix_Steps:")
            print(evaluate(df.loc[i]['soln'], df.loc[i]['eqn']))
            steps.append('NA')
            metrics.append('NA')
    df['steps'] = steps
    df['metrics'] = metrics
    print("Number of Errors: "+str(error_count))
    df.to_csv(outputSolnPath)

def computeResults(ds, lemma, conpole):
    '''
    Computes metrics table in paper, takes as arguments the solutions files for DreamSolver, Lemma, and ConPoLe.

    Inputs: 
        - DreamSolver Solutions file with metric function computed
        - Lemma Solutions file with metric function computed
        - ConPoLe Solutions file with metric function computed

    Returns:
        - None 
    '''
    df_ds = pd.read_csv(ds)
    df_lm = pd.read_csv(lemma)
    df_cp = pd.read_csv(conpole)
    lm_numsolv = 0
    cp_numsolv = 0
    lm_cp_rel_conc = 0
    lm_cp_rel_conc_denom = 0 
    ds_cp_rel_conc = 0
    ds_cp_rel_conc_denom = 0
    lm_soleq = df_lm['Equation Number'].values.tolist()
    cp_soleq = df_cp['Equation Number'].values.tolist()
    for soleq in range(len(df_ds['equation_number'])):
        ctr1=False
        ctr2=False        
        if df_ds.loc[soleq]['equation_number'] in lm_soleq:
            lm_numsolv+=1
            ctr1=True
        if df_ds.loc[soleq]['equation_number'] in cp_soleq:    
            cp_numsolv+=1
            ctr2=True
        if ctr1 and ctr2:
            lm_ind = lm_soleq.index(df_ds.loc[soleq]['equation_number'])
            cp_ind = cp_soleq.index(df_ds.loc[soleq]['equation_number'])
            print("DreamSolver: ")
            print(df_ds.loc[soleq]["steps"])
            print("Lemma: ")
            print(df_lm.loc[lm_ind]["soln"])
            print("ConPoLe: ")
            print(df_cp.loc[cp_ind]["soln"])
            lm_cp_rel_conc += (int(df_cp.loc[cp_ind]["metrics"])-int(df_lm.loc[lm_ind]["metrics"]))/int(df_cp.loc[cp_ind]["metrics"])
            lm_cp_rel_conc_denom+=1
            ds_cp_rel_conc+=(int(df_cp.loc[cp_ind]["metrics"])-int(df_ds.loc[soleq]["metrics"]))/int(df_cp.loc[cp_ind]["metrics"])
            ds_cp_rel_conc_denom +=1
    print("%age of eqs ConPoLe solved: " + str(cp_numsolv/len(df_ds['equation_number'])))
    print("%age of eqs Lemma solved: " + str(lm_numsolv/len(df_ds['equation_number'])))
    print("Lemma-ConPoLe metric: " + str(lm_cp_rel_conc/lm_cp_rel_conc_denom))
    print("DS-ConPoLe metric: " + str(ds_cp_rel_conc/ds_cp_rel_conc_denom))

def genShorterEq(eq):
    '''
    Given an infix-notation string of an equation that DreamSolver cannot solve, generate a shorter, simpler equation. Assumes at most one bracket exists in infix form between two consecutive operations e.g. there is only one bracket between + and * in ((2/x)+3)*x)=5.
    '''

    eq = eq.replace(" ", "")
    operator_list = []
    for i in range(len(eq)):
        if eq[i] in ["+", "-", "*", "/", "="]:
            operator_list.append(i)
    if len(operator_list)<2:
        return eq
    rand = random.randint(0, len(operator_list)-1)
    chosen_op_ind = operator_list[rand]
    if eq[chosen_op_ind]=="=":
        if rand!=0:
            chosen_op_ind=operator_list[rand-1]
            rand -= 1
        else:
            chosen_op_ind=operator_list[rand+1]
            rand += 1
    end = None
    if rand<len(operator_list)-1:
        end = operator_list[rand+1]
    else:
        end = len(eq)
    new_eq = eq[:chosen_op_ind] + eq[end:]
    unmatched = None
    for i in range(chosen_op_ind):
        if new_eq[i]=="(":
            close = matchBr(new_eq, i)
            if close==None:
                unmatched = i
    if unmatched!=None:
        new_eq = new_eq[:unmatched] + new_eq[unmatched+1:]
    return new_eq

def genAdditionalEquations(dsSolnPathOriginal, eqnPath, newDatasetPath,  dsSolnPathCurrIter=None):
    ''' 
    Given a .csv file containing solution program expressions copied from the terminal output of DreamSolver, identify the equations that DreamSolver failed to solve and generate a shorter variation of the equation.
    
    Inputs:
        - dsSolnPathOriginal is the .csv file containing the original solution expressions generated purely by training DreamSolver
        - eqnPath is the .csv file containing the original training equations
        - newDatasetPath is a string containing a path to the .csv where we would like to store our newly generated equations
        - dsSolnPathCurrIter is the optional .csv file to be used if we generated equations once and DreamSolver still failed to find any solutions.

    Returns:
        - None
    '''
    start = 0
    df = None
    if dsSolnPathCurrIter == None:
        df = pd.read_csv(dsSolnPathOriginal)
    else:
        df_old = pd.read_csv(dsSolnPathOriginal)
        df = pd.read_csv(dsSolnPathCurrIter)
        start = df_old.shape[0]
    df_eq = pd.read_csv(eqnPath)
    df_eq = df_eq.drop(columns=df_eq.columns[0])
    equation_numbering_list = []
    unsolved_infix_eq_list = []

    for i in range(start, df.shape[0]):
        or_eq = df.loc[i]['output']
        or_eq_split = or_eq.split(' ')
        if or_eq_split[0]=="MISS":
            eqn_no = or_eq_split[1][2:]
            unsolved_infix_eq_list.append(str(df_eq.iat[int(eqn_no), 0]))
            equation_numbering_list.append(eqn_no)
    df_neweq = pd.DataFrame({'Infix_Eq': [], 'Prefix_Eg': [], 'Working': [], 'Infix_Sol': [], 'Prefix_Sol': []})
    for eq in unsolved_infix_eq_list:
        equation = genShorterEq(eq)
        df_neweq.loc[len(df_neweq.index)] = [eq, None, None, None, None]
        df_neweq.loc[len(df_neweq.index)] = [equation, None, None, None, None]
    df_neweq.to_csv(newDatasetPath, index=False)
    mdpc.csv_infix_to_csv_prefix(newDatasetPath, newDatasetPath)

if __name__ == "__main__":

    '''
    Tests for evaluate() function for step-by-step solution generation
    '''

    '''
    test_case_1 = "(lambda $0)" #te273
    test_case_2 = "(lambda (#(lambda (_simplify (_dist $0 1) 0)) $0))" #te28
    test_case_3 = "(lambda (#(lambda (#(lambda (_simplify (_swap $0 0) 0)) (_rrotate (_swap $0 3) 2))) (#(lambda (_simplify (_rrotate (_sub (_simplify $0 0) 3) 1) 0)) (#(lambda (_simplify (_rrotate (_sub (_simplify $0 0) 3) 1) 0)) (_swap (#(lambda (#(lambda (_simplify (_swap $0 0) 0)) (_rrotate (_swap $0 3) 2))) $0) 1)))))" #te40

    print(evaluate(test_case_1, "(= (x) (/ (-1) (2)))"))
    print(evaluate(test_case_2, "(= (+ (* (-1) (x)) (* (2) (x))) (-3))"))
    print(evaluate(test_case_3, "(= (1) (+ (* (2) (x)) (3)))"))

    clSolnEval('mathDomainOutputs/generatedConpoleSolutions.csv', 'mathDomainOutputs/generatedConpoleSolutions-CScores.csv')
    clSolnEval('mathDomainOutputs/generatedLemmaSolutions.csv', 
    'mathDomainOutputs/generatedLemmaSolutions-CScores.csv') 

    s = "(= (+ (- (x) (5)) (3)) (2))"
    print(mdp._lrotate(mdp._rrotate(s, 1), 1))
    
    #dsSolnFormat('dc134soln.csv', 'conpoleDatasetPrefix.csv', 'dc134solnformatted.csv')
    dsSolnEval('dc134solnformatted.csv', 'dc134solnevaluated.csv')
    computeResults('dc134solnevaluated.csv', 'generatedLemmaSolutions-CScores.csv','generatedConpoleSolutions-CScores.csv')

    '''

    '''
    Tests for evaluting shorter equation generation

    #Copy Testing Equation to bin before running this
    df = pd.read_csv('trainingEquationsModified.csv')
    for i in range(df.shape[0]):
        eq = str(df.iat[i, 1])
        print(genShorterEq(eq))
    '''

    '''
    Test for evaluating additional equation generation
    '''
    #genAdditionalEquations('ds75of123soln6-21-2023.csv', 'trainingEquationsModified.csv', 'newDatasetTestingGenAdditionalEquations.csv')
    
    genAdditionalEquations('ds209of284soln7-10-2023.csv', 'conpoleDatasetPrefix.csv', 'newTestingEquations209of284soln7-10-2023.csv')