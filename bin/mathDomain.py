import datetime
import os
import random

import binutil  # required to import from dreamcoder modules

from dreamcoder.ec import commandlineArguments, ecIterator
from dreamcoder.grammar import Grammar
from dreamcoder.program import Primitive
from dreamcoder.task import Task
from dreamcoder.type import arrow, tint, tstr
from dreamcoder.utilities import numberOfCPUs

from dreamcoder.domains.re2.main import StringFeatureExtractor

ops = ["+", "-", "*", "/"]


class Tree:

  def __init__(self, root, left="None", right="None") -> None:
    #Initialization of tree with root value and left and right subtrees
    self.root = root
    self.left = left
    self.right = right

  def __eq__(self, __o: object) -> bool:
    #Enables equality comparison of trees
    return isinstance(
      __o, Tree
    ) and self.root == __o.root and self.left == __o.left and self.right == __o.right

  def __repr__(self) -> str:
    #String representation of the tree
    return "(" + str(self.root) + " " + str(self.left) + " " + str(
      self.right) + ")"

  def __typerepr__(self) -> str:
    #Shows the types present in the tree, mostly concerned with str/int working, hence the [-6:-1] index range
    leftType = str(type(self.left))
    rightType = str(type(self.right))
    if (leftType == "<class '__main__.Tree'>"):
      leftType = self.left.__typerepr__()
    if (rightType == "<class '__main__.Tree'>"):
      rightType = self.right.__typerepr__()
    return "(" + str(type(
      self.root))[-6:-1] + " " + leftType + " " + rightType + ")"


def isNum(x):
  return (isinstance(x, int) or isinstance(x, float))


def intConvertable(s):
  try:
    int(s)
    return True
  except ValueError:
    return False


def floatConvertable(s):
  try:
    float(s)
    return True
  except ValueError:
    return False


def detreefy(tree):
  #converts tree into prefix equation string
  if tree == "None":
    return ""
  left = detreefy(tree.left)
  right = detreefy(tree.right)
  if left != "":
    left = " " + str(left)
  if right != "":
    right = " " + str(right)
  return "(" + str(tree.root) + str(left) + str(right) + ")"


def matchBracket(string, ind):
  #finds corresponding matching bracket of the bracket in prefix notation
  if string[ind] == "(":
    brCount = 1
    for i in range(ind + 1, len(string)):
      if (string[i] == "("):
        brCount += 1
      if (string[i] == ")"):
        brCount -= 1
      if brCount == 0:
        return i
  elif string[ind] == ")":
    brCount = 1
    for i in range(ind - 1, 0, -1):
      if (string[i] == "("):
        brCount -= 1
      if (string[i] == ")"):
        brCount += 1
      if brCount == 0:
        return i
  return "Error"


def treefy(eq):
  #converts prefix equation string to tree
  #operations must be in ops or "="
  #numbers must be int or floats
  #no space between brackets and operations succeeding them
  #(+ (- (x) (3)) (y))
  if eq == "None":
    return "None"
  newEq = eq[1:-1]
  fstArgInd = newEq.find("(")
  sndArgInd = newEq.rfind(")")
  fstArgMatch = "None"
  sndArgMatch = "None"
  args = [newEq.split(" ")[0]]
  if fstArgInd != -1:
    fstArgMatch = matchBracket(newEq, fstArgInd)
  if sndArgInd != -1:
    sndArgMatch = matchBracket(newEq, sndArgInd)
  if (fstArgInd != -1 and sndArgInd != -1):
    if (fstArgInd != sndArgMatch):
      args.append(newEq[fstArgInd:fstArgMatch + 1])
      args.append(newEq[sndArgMatch:sndArgInd + 1])
    else:
      args.append(newEq[fstArgInd:fstArgMatch + 1])
  if (intConvertable(args[0])):
    args[0] = int(args[0])
  elif (floatConvertable(args[0])):
    args[0] = float(args[0])
  while len(args) < 3:
    args.append("None")
  return Tree(args[0], treefy(args[1]), treefy(args[2]))


def _rrotateHelper(s):
  #Right rotation of tree
  #originalRoot = Q
  #upperLeft = P
  #upperRight = C
  #bottomLeft = A
  #bottomRight = B
  #follow diagram at https://en.wikipedia.org/wiki/File:Tree_rotation.png
  eqTree = treefy(s)
  if eqTree.root in ops and eqTree.left.root in ops:
    originalRoot = eqTree.root
    upperLeft = eqTree.left.root
    upperRight = eqTree.right
    bottomLeft = eqTree.left.left
    bottomRight = eqTree.left.right
    rightSub = Tree(originalRoot, bottomRight, upperRight)
    newTree = Tree(upperLeft, bottomLeft, rightSub)
    return detreefy(newTree)
  return s


def _lrotateHelper(s):
  #Left rotation of tree
  #originalRoot = P
  #upperLeft = A
  #upperRight = Q
  #bottomLeft = B
  #bottomRight = C
  #follow diagram at https://en.wikipedia.org/wiki/File:Tree_rotation.png
  eqTree = treefy(s)
  if eqTree.root in ops and eqTree.right.root in ops:
    originalRoot = eqTree.root
    upperLeft = eqTree.left
    upperRight = eqTree.right.root
    bottomLeft = eqTree.right.left
    bottomRight = eqTree.right.right
    leftSub = Tree(originalRoot, upperLeft, bottomLeft)
    newTree = Tree(upperRight, leftSub, bottomRight)
    return detreefy(newTree)
  return s


def _genSub(s):
  #Generates all subtrees of a given tree
  eqTree = treefy(s)
  if s == "None":
    return []
  elif (eqTree.left == "None" and eqTree.right == "None"):
    return [s]
  else:
    left = [] if eqTree.left == "None" else _genSub(detreefy(eqTree.left))
    right = [] if eqTree.right == "None" else _genSub(detreefy(eqTree.right))
    return [s] + left + right


def _reconstruct(i, old, newT):
  #Reconstructs a new tree by swapping in newT in the i-th indexed subtree of old. So if subtree "k" is at the i-th index of result of genSub(old), "k" in old gets replaced by new.
  subList = _genSub(old)
  oldT = treefy(old)
  if (i > len(subList)):
    return oldT
  elif (i == 0):
    return treefy(newT)
  else:
    leftLength = len(_genSub(detreefy(oldT.left)))
    if (i <= leftLength):
      return Tree(oldT.root, _reconstruct(i - 1, detreefy(oldT.left), newT),
                  oldT.right)
    else:
      return Tree(oldT.root, oldT.left,
                  _reconstruct(i - 1 - leftLength, detreefy(oldT.right), newT))


def _treeOp(s, i, op):
  #Performs tree operation on i-th subtree
  allSubs = _genSub(s)
  modifiedSub = op(allSubs[i])
  return detreefy(_reconstruct(i, s, modifiedSub))


def _op(s, x, op):
  #Performs operation on x on both sides of tree.
  eqTree = treefy(s)
  if eqTree.root == '=':
    newLeft = Tree(op, eqTree.left, Tree(x))
    newRight = Tree(op, Tree(x), eqTree.right)
    newTree = Tree("=", newLeft, newRight)
    return detreefy(newTree)
  return s


def _swapHelper(s):
  #Swaps left and right subtrees in a tree
  eqTree = treefy(s)
  newTree = Tree(eqTree.root, eqTree.right, eqTree.left)
  return detreefy(newTree)


def _evalTree(op, left, right):
  if op == "+":
    return detreefy(Tree(left + right))
  if op == "-":
    return detreefy(Tree(left - right))
  if op == "*":
    return detreefy(Tree(left * right))
  if op == "/":
    return detreefy(Tree(left // right))
  return detreefy(Tree(op, left, right))


def _simplifyHelper(s):
  #Simplifies the tree where possible
  eqTree = treefy(s)
  if (eqTree.left == "None" and eqTree.right == "None"):
    return detreefy(eqTree)
  else:
    left = treefy(_simplifyHelper(detreefy(eqTree.left)))
    right = treefy(_simplifyHelper(detreefy(eqTree.right)))
    leftSimple = left.root
    rightSimple = right.root
    if (isNum(leftSimple) and isNum(rightSimple)):
      return _evalTree(eqTree.root, leftSimple, rightSimple)
    elif (eqTree.root == "+" and leftSimple == 0) or (eqTree.root == "*"
                                                      and leftSimple == 1):
      return detreefy(right)
    elif ((eqTree.root == "+" or eqTree.root == "-") and rightSimple == 0) or (
      (eqTree.root == "*" or eqTree.root == "/") and rightSimple == 1):
      return detreefy(left)
    elif ((eqTree.root == "-" and left == right and left.root != "None")
          or (eqTree.root == "*" and (leftSimple == 0 or rightSimple == 0))):
      return detreefy(Tree(0))
    elif (eqTree.root == "/" and left == right and left.root != "None"):
      return detreefy(Tree(1))
    else:
      return detreefy(Tree(eqTree.root, left, right))


def _add(s, x):
  return _op(s, x, "+")


def _sub(s, x):
  return _op(s, x, "-")


def _mult(s, x):
  return _op(s, x, "*")


def _div(s, x):
  return _op(s, x, "/")


def _rrotate(s, i):
  return _treeOp(s, i, _rrotateHelper)


def _lrotate(s, i):
  return _treeOp(s, i, _lrotateHelper)


def _simplify(s, i):
  return _treeOp(s, i, _simplifyHelper)


def _swap(s, i):
  return _treeOp(s, i, _swapHelper)


'''
##Python Tests

eq = "(+ (- (/ (+ (x) (3)) (5)) (3)) (y))"
testTree = treefy(eq)
#print(testTree)
#print(testTree.__typerepr__())
#print(detreefy(testTree))
#testTree2 = treefy("(5)")
#print(testTree2.__typerepr__())
#print(_lrotate(_rrotate(eq, 0), 0))
eq2 = "(= (+ (- (/ (+ (x) (3)) (5)) (3)) (y)) (y))"
#print(_swap(eq2, 0))
eq3 = "(= (x) (+ (5) (3)))"
eq4 = "(= (x) (- (5) (3)))"
eq5 = "(= (x) (* (5) (3)))"
eq6 = "(= (x) (/ (6) (3)))"
print(_simplify(eq6, 0))
print(_simplify(_mult(eq3, 5), 0))
'''
'''
##OCaml Tests

#String Representation Test

print(detreefy(Tree(4, Tree(2, Tree(1), Tree(3)), Tree(5, Tree(6), Tree(7)))))
#Output: (4 (2 (1) (3)) (5 (6) (7)))

#Equality Test
t1 = Tree(4, Tree(2, Tree(1), Tree(3)), Tree(5, Tree(6), Tree(7)))
t2 = Tree(4, Tree(2, Tree(1), Tree(3)), Tree(5, Tree(6), Tree(7)))
print(t1==t2)
#Output: True

#Treefy and Detreefy Test
print(detreefy(treefy("(4 (2 (1) (3)) (5 (6) (7)))")))
#Output: "(4 (2 (1) (3)) (5 (6) (7)))"

#Rotation Tests
eqTree = "()"
print(_rrotate(eqTree, 0))
print(_lrotate(eqTree, 0))
print(_lrotate(_rrotate(eqTree, 0), 0))
#Output:
#()
#()
#()

eqTree = "(+ (- (/ (+ (x) (3)) (5)) (3)) (y))"
print(_rrotate(eqTree, 0))
print(_lrotate(eqTree, 0))
print(_lrotate(_rrotate(eqTree, 0), 0))

#Output:
#(- (/ (+ (x) (3)) (5)) (+ (3) (y)))
#(+ (- (/ (+ (x) (3)) (5)) (3)) (y))
#(+ (- (/ (+ (x) (3)) (5)) (3)) (y))

#Subtree Generation Test
eqTree = "(+ (- (/ (+ (7) (3)) (5)) (3)) (y))"
print(_genSub(eqTree))
#Output: ['(+ (- (/ (+ (7) (3)) (5)) (3)) (y))', '(- (/ (+ (7) (3)) (5)) (3))', '(/ (+ (7) (3)) (5))', '(+ (7) (3))', '(7)', '(3)', '(5)', '(3)', '(y)']

#Arithmetic Operation and Swap Test

eqTree = "(= (- (/ (+ (7) (3)) (5)) (3)) (y))"
print(_add(eqTree, 5))
print(_sub(eqTree, 4))
print(_div(eqTree, 3))
print(_mult(eqTree, 2))
print(_swap(eqTree, 0))
#Output:
#(= (+ (- (/ (+ (7) (3)) (5)) (3)) (5)) (+ (y) (5)))
#(= (- (- (/ (+ (7) (3)) (5)) (3)) (4)) (- (y) (4)))
#(= (/ (- (/ (+ (7) (3)) (5)) (3)) (3)) (/ (y) (3)))
#(= (* (- (/ (+ (7) (3)) (5)) (3)) (2)) (* (y) (2)))
#(= (y) (- (/ (+ (7) (3)) (5)) (3)))

#Simplification Tests

eqTree = "(= (- (/ (+ (7) (3)) (5)) (3)) (y))"
print(_simplify(eqTree, 3))
#Output: (= (- (/ (10) (5)) (3)) (y))

eqTree = "()"
print(_simplify(eqTree, 0))
#Output: ()

# Test to convert an entire equation to solution tree 
eqTree = "(= (/ (+ (7) (3)) (5)) (+ (3) (y)))"
print(_swap(_simplify(_simplify(_simplify(_simplify(_simplify(_lrotate(_sub(eqTree, 3), 8), 3), 2), 1), 3), 2), 0))
#Output: (= (y) (-1))
'''

def exampleX(x):
    return {"i": "(= ("+str(x)+") (x))", "o": "(= (x) ("+str(x)+"))"}

def get_tstr_task(item):
    return Task(
        item["name"],
        arrow(tstr, tstr),
        [((ex["i"],), ex["o"]) for ex in item["examples"]],
    )

if __name__ == "__main__":

    args = commandlineArguments(
        enumerationTimeout=10, activation='tanh',
        iterations=10, recognitionTimeout=3600,
        a=3, maximumFrontier=10, topK=2, pseudoCounts=30.0,
        helmholtzRatio=0.5, structurePenalty=1.,
        CPUs=numberOfCPUs(),
        featureExtractor=StringFeatureExtractor)
    
    timestamp = datetime.datetime.now().isoformat()
    outdir = 'experimentOutputs/demo/'
    os.makedirs(outdir, exist_ok=True)
    outprefix = outdir + timestamp
    args.update({"outputPrefix": outprefix})

    primitives = [
        Primitive("mathDomain_add", arrow(tstr, tint, tstr), _add),
        Primitive("mathDomain_sub", arrow(tstr, tint, tstr), _sub),
        Primitive("mathDomain_mult", arrow(tstr, tint, tstr), _mult),
        Primitive("mathDomain_div", arrow(tstr, tint, tstr), _div),
        Primitive("mathDomain_rrotate", arrow(tstr, tint, tstr), _rrotate),
        Primitive("mathDomain_lrotate", arrow(tstr, tint, tstr), _lrotate), 
        Primitive("mathDomain_simplify", arrow(tstr, tint, tstr), _simplify),
        Primitive("mathDomain_swap", arrow(tstr, tint, tstr), _swap)
    ]

    grammar = Grammar.uniform(primitives)

    def ex1(): return exampleX(1)
    def ex2(): return exampleX(2)
    def ex3(): return exampleX(3)
    def ex4(): return exampleX(4)

    training_examples = [
        {"name": "add1", "examples": [ex1() for _ in range(5000)]},
        {"name": "add2", "examples": [ex2() for _ in range(5000)]},
        {"name": "add3", "examples": [ex3() for _ in range(5000)]},
    ]

    training = [get_tstr_task(item) for item in training_examples]

    testing_examples = [
        {"name": "add4", "examples": [ex4() for _ in range(500)]},
    ]
    
    testing = [get_tstr_task(item) for item in testing_examples]
    
    generator = ecIterator(grammar,
                           training,
                           testingTasks=testing,
                           **args)
    for i, _ in enumerate(generator):
        print('ecIterator count {}'.format(i))