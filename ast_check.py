"""
Double checks that the tiers of the procedures match and
also performs linking the function calls to the exact function
def which they will execute at runtime
"""



import glass
import glasstokenize as tokenize
import build_ast

Problem = glass.Problem
TokProblem = glass.TokProblem



def checkProcTiers(syntaxTree, allVars, problems):
    for syntax in syntaxTree:
        if syntax.syntaxType == build_ast.PROCDEF:
            checkProcDef(syntax, problems)
        else:
            checkLine(None, syntax, problems)

def checkProcDef(procDef, problems):
    checkBlock(procDef, procDef.code, problems)



def checkBlock(procDef, code, problems):# code is list(build_ast.Syntax)
    for codeLine in code:
        checkLine(procDef, codeLine, problems)
        if isinstance(codeLine, build_ast.Block):
            checkBlock(procDef, codeLine.code, problems)
        if isinstance(codeLine, build_ast.Try):
            if codeLine.catch != None:
                checkBlock(procDef, codeLine.catch.code, problems)
        if isinstance(codeLine, build_ast.If):
            ifStatement = codeLine

            while ifStatement.elifBlock != None:
                checkBlock(procDef, ifStatement.elifBlock.code, problems)
                ifStatement = ifStatement.elifBlock
                checkLine(procDef, ifStatement, problems)

            if ifStatement.elseBlock != None:
                checkBlock(procDef, ifStatement.elseBlock.code, problems)
def checkLine(procDef, codeLine, problems):
    if codeLine.syntaxType in {build_ast.VARSET, build_ast.FOREACH, build_ast.IF, build_ast.PROCCALL, build_ast.OUTPUT}:
        if codeLine.syntaxType == build_ast.VARSET:
            exp = codeLine.expression

            if procDef != None and not procDef.exemptFromChecks:
                if procDef != None and codeLine.varType == build_ast.GLOBAL_VARIABLE and procDef.tier < 3:
                    TokProblem("Tier " + str(procDef.tier) + " procedure '" + getNiceHeader(procDef) + "' modifies a global variable when only tier 3 or higher procedures can modify global variables. Try using '[' and ']' in the procedure header to make the procedure tier 3" ,codeLine.startToken, problems)
                if procDef != None and codeLine.apostrophe_s_VarNames != None and procDef.tier < 2:
                    TokProblem("Tier " + str(procDef.tier) + " procedure '" + getNiceHeader(procDef) + "' modifies an object when only tier 2 or higher procedures can modify objects. Try using '{' and '}' in the procedure header to make the procedure tier 2" ,codeLine.startToken, problems)


        elif codeLine.syntaxType == build_ast.FOREACH:
            exp = codeLine.iteratorExpression
            findProcDefOfProcCall(codeLine, problems)
        elif codeLine.syntaxType == build_ast.IF:
            exp = codeLine.ifTestExpression
        
        elif codeLine.syntaxType == build_ast.OUTPUT:
            exp = codeLine.expression
        elif codeLine.syntaxType == build_ast.PROCCALL:
            checkProcCall(procDef, codeLine, problems)
            return


        if exp != None:
            checkExpression(procDef, exp, problems)
            

def checkExpression(parentProcDef, exp, problems):
    if exp.syntaxType == build_ast.PROCCALL:
        checkProcCall(parentProcDef, exp, problems)
    elif exp.syntaxType == build_ast.VARACCESS:

        if parentProcDef != None and parentProcDef.tier < 3:
            if exp.varType == build_ast.GLOBAL_VARIABLE and (not exp.isConstantVariableAccess):
                TokProblem("Tier " + str(parentProcDef.tier) + " procedure cannot access global variables unless they are constants.", exp.startToken, problems)


def checkProcCall(parentProcDef, procCall, problems):
    expressions = []
    for tpe in procCall.tokensAndParamExpressions:
        if isinstance(tpe, build_ast.Expression):
            expressions.append(tpe)

    for exp in expressions:
        checkExpression(parentProcDef, exp, problems)
            

    procDefToBeExecuted = findProcDefOfProcCall(procCall, problems)#PERFORMS LINKING HERE

    childTier = procDefToBeExecuted.tier


    if parentProcDef != None and not parentProcDef.exemptFromChecks:
        parentTier = parentProcDef.tier
        if childTier > parentTier:
            parentProcSig = parentProcDef.procSignature[0].tokenData + " ".join([str(t.tokenData) for t in parentProcDef.procSignature[1].tokenData]) + parentProcDef.procSignature[2].tokenData
            TokProblem("Tier " + str(parentTier) + " function '" + parentProcSig + "' calls a Tier " + str(childTier) + " function" ,procCall.startToken, problems)
    
    
    
    
    
    
    
    #check to see if the proc call parenthesis are the same as the proc def ones

    procCallTier = -1
    openParen = procCall.startToken.tokenData
    if openParen == "(": procCallTier = 1
    elif openParen == "{": procCallTier = 2
    elif openParen == "[": procCallTier = 3
    elif openParen == "<": procCallTier = 4

    if procCallTier < procDefToBeExecuted.tier:
        keys = [None,"( and )", "{ and }", "[ and ]", "< and >"]
        TokProblem("Must use " + keys[procDefToBeExecuted.tier] + " for this procedure call, instead of " + keys[procCallTier], procCall.startToken, problems)




def getNiceHeader(procDef):
    return procDef.procSignature[0].tokenData + " ".join([str(t.tokenData) for t in procDef.procSignature[1].tokenData]) + procDef.procSignature[2].tokenData




#finds the exact proc def that a proc call will refer to at runtime.
#this function also sets a pointer inside the proc call object to directly
#point to the proc call... for future reference
def findProcDefOfProcCall(procCall, problems):
    #isSuperCall = procCall.callSuper
    
    procDef = procCall.procDef
    while procDef.overridedBy != None:
        procDef = procDef.overridedBy
    """
    if isSuperCall:
        if procDef.overrides != None:
            procDef = procDef.overrides
        else:
            TokProblem("Code attempts to call the super function but there is no super function", procCall.startToken, problems)
    """
    procCall.procDefThatIsExecuted = procDef
    return procDef

    

