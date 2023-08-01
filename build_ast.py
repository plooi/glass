
from lib2to3.pgen2 import token
from pickle import GLOBAL
import sys
import os

from numpy import inner
import glass
import glasstokenize as tokenize
import ast_check
import interpreter
import glassTypes as types

Problem = glass.Problem
TokProblem = glass.TokProblem

procDefinitionKeyword = "howto"
procOverrideKeyword = "before"
forEachKeyword = "foreach"
ifKeyword = "if"
elifKeyword = "elif"
elseKeyword = "else"
tryKeyword = "try"
catchKeyword = "catch"
inKeyword = "in"
returnKeyword = "output"
returnTypeKeyword = "outputs"
superKeyword = "super"
globalKeyword = "@"
exemptKeyword = "exempt"
noKeyword = "no"

keywords = {procDefinitionKeyword, procOverrideKeyword, forEachKeyword, ifKeyword, elifKeyword, elseKeyword, tryKeyword, catchKeyword, inKeyword, returnKeyword, returnTypeKeyword, superKeyword, globalKeyword, exemptKeyword, noKeyword}


GLOBAL_VARIABLE = 0
LOCAL_VARIABLE = 1





PARAM = 0
PROCDEF = 1
FOREACH = 2
IF = 3
TRY = 4
CATCH = 5
VARSET = 6
EXPRESSION = 7
LITERAL = 8
VARACCESS = 9
PROCCALL = 10
OUTPUT = 11


class Syntax:
    def __init__(self, token):
        self.startToken = token
        self.syntaxType = None

    def __str__(self):
        vars = dict(self.__dict__)
        if "code" in vars: vars["code"] = str(len(vars["code"])) + " lines..."

        ret = str(self.__class__) + "->" + str(vars)
        if "code" in self.__dict__:
            ret += "\nBlockCode:"
            for line in self.code:
                ret += "\n    " + repr(line)
        return ret
    def __repr__(self):
        return str(self)


class Block(Syntax):
    def __init__(self, token):
        super().__init__(token)
        self.code = []#array of LineOfCode
        self.syntaxType = None

class Param(Syntax):
    def __init__(self, token, name):
        super().__init__(token)
        self.name = name
        self.varType = None
        self.varID = None
        self.isConstant = False
        self.syntaxType = PARAM
        self.inputDatatype = None
        self.inputDatatypeToken = None


#get's a proc def's tier based on what type of parenthesis are used in the 
#procedure's header
def getProcDefTier(procDef, problems):
    parenType = procDef.procSignature[0].tokenData
    if parenType == "(": return 1
    if parenType == "{": return 2
    if parenType == "[": return 3
    if parenType == "<": return 4

    TokProblem("Invalid parenthesis type", procDef.startToken, problems)
    quit()


class ProcDef(Block):
    def __init__(self, token, isOverride):
        super().__init__(token)
        self.isOverride = isOverride
        self.numParams = -1#int
        self.procSignature = []#array of Tokens
        self.procSignatureWithoutStarsOrParen = []
        self.pattern = None#string. p stands for parameter, w stands for just a word
        self.overridedBy = None #points to another proc def which is the override (if there is an override) 
        self.overrides = None#points toanother procDef that this proc def overrides (if this one is an override) THIS IS THE "SUPER" FUNCTION
        self.params = []
        self.header = None
        self.numLocalVars = -1
        self.syntaxType = PROCDEF

        self.tier = None
        self.exemptFromChecks = False
        self.returnTypeToken = None
        self.returnType = None
    def getFriendlyName(self):
        return self.header.lower().replace("_", "<INPUT>")
    def getRawHeaderCode(self):
        t = self.startToken
        file = t.file
        lineNumber = t.lineNumber
        
        f = open(file,"r")
        i = 0
        for line in f:
            if i == lineNumber:
                return line.strip()
            i += 1


    def finalInit(self, allProcedures, allOpenEndedProcCalls, problems):
        procedures = allProcedures
        self.header = ""
        for i in range(len(self.pattern)):
            if self.pattern[i] == "w":
                self.header += self.procSignatureWithoutStarsOrParen[i].tokenData.upper()
            else:
                self.header += "_"
        
        if self.isOverride:
            if self.header not in procedures:
                TokProblem("This procedure is declared as an override, but there's no existing procedure has the same input pattern of '" + self.header.replace("_","(input)")+"'", self.startToken, problems)
            else:
                #do the override

                procedureWithoutOverride = procedures[self.header]
                while True:
                    if procedureWithoutOverride.overridedBy == None:
                        break
                    if procedureWithoutOverride.overridedBy != None:
                        procedureWithoutOverride = procedureWithoutOverride.overridedBy

                procedureWithoutOverride.overridedBy = self
                self.overrides = procedureWithoutOverride


                if self.returnType != procedureWithoutOverride.returnType:
                    TokProblem("ERROR:\nThis before procedure at line " + str(self.startToken.lineNumber+1) + " of " + self.startToken.file + 
                    ":~~~~~~~~ " + self.getRawHeaderCode() + " ~~~~~~~~" + 
                    "\nModifies this procedure at line " +str(procedureWithoutOverride.startToken.lineNumber+1) + " of " + procedureWithoutOverride.startToken.file + 
                    ":~~~~~~~~ " + procedureWithoutOverride.getRawHeaderCode() + " ~~~~~~~~"+ 
                    "\n\nBut the two procedures have different output types. They must have the exact same output types in order for one to be a \"before\" of the other.\n\n", self.startToken, problems, autoStr=False)
                inputTypesNotSame = False
                for i in range(len(self.params)):
                    if self.params[i].inputDatatype != procedureWithoutOverride.params[i].inputDatatype:
                        inputTypesNotSame = True
                        break
                if inputTypesNotSame:
                    TokProblem("ERROR:\nThis before procedure at line " + str(self.startToken.lineNumber+1) + " of " + self.startToken.file + 
                    ":~~~~~~~~ " + self.getRawHeaderCode() + " ~~~~~~~~" + 
                    "\nModifies this procedure at line " +str(procedureWithoutOverride.startToken.lineNumber+1) + " of " + procedureWithoutOverride.startToken.file + 
                    ":~~~~~~~~ " + procedureWithoutOverride.getRawHeaderCode() + " ~~~~~~~~"+ 
                    "\n\nBut the two procedures have different input types. They must have the exact same input types in order for one to be a \"before\" of the other.\n\n", self.startToken, problems, autoStr=False)

        else:
            #replace the old function (or make a new one)
            procedures[self.header] = self

            if self.header in allOpenEndedProcCalls:
                for procCall in allOpenEndedProcCalls[self.header]:
                    procCall.procDef = self
                del allOpenEndedProcCalls[self.header]

        self.tier = getProcDefTier(self, problems)



    #def __str__(self):
    #    return self.header + ":" + str(id(self))


class ForEach(Block):
    def __init__(self, token):
        super().__init__(token)
        self.varName = None#token
        self.iteratorExpression = None#expression
        self.varType = None
        self.varID = None
        self.isConstant = False
        self.syntaxType = FOREACH
        self.procDef = None# the proc def of the base function (won't point to overrides)
        self.procDefThatIsExecuted = None#if the original proc def gets overrided, then this will point to the 
    def finalInit(self, allProcedures, allOpenEndedProcCalls, problems):
        inputPattern = "ITERATE_"
        if inputPattern in allProcedures:
            self.procDef = allProcedures[inputPattern]
            
        else:
            if inputPattern in allOpenEndedProcCalls:
                allOpenEndedProcCalls[inputPattern].append(self)
            else:
                allOpenEndedProcCalls[inputPattern] = [self]

class If(Block):
    def __init__(self, token):
        super().__init__(token)
        self.ifTestExpression = None#expression
        self.syntaxType = IF
        self.elifBlock = None
        self.elseBlock = None
class Else(Block):
    def __init__(self, token):
        super().__init__(token)
        self.catch = None
        self.syntaxType = TRY
class Try(Block):
    def __init__(self, token):
        super().__init__(token)
        self.catch = None
        self.syntaxType = TRY
class Catch(Block):
    def __init__(self, token):
        super().__init__(token)
        self.varName = None
        self.varType = None
        self.varID = None
        self.isConstant = False
        self.syntaxType = CATCH

class VarSet(Syntax):
    def __init__(self, token, varName=None, type=LOCAL_VARIABLE):
        super().__init__(token)
        self.varName = varName#Token
        self.apostrophe_s_VarNames = None
        self.varType = type
        self.varID = None

        self.expression = None #Expression
        self.syntaxType = VARSET

        self.isConstant = False




class Expression(Syntax):
    def __init__(self, token):
        super().__init__(token)
        self.syntaxType = EXPRESSION

class Literal(Expression):
    def __init__(self, token, literalValue):
        super().__init__(token)
        self.literalValue = literalValue
        self.syntaxType = LITERAL
    
class VarAccess(Expression):
    def __init__(self, token, varName):
        super().__init__(token)
        self.varName = varName#token
        self.apostrophe_s_VarNames = None
        self.syntaxType = VARACCESS

        self.varType = None
        self.varID = None

        self.isConstantVariableAccess = False
        
class ProcCall(Expression):
    def __init__(self, token, parenType):
        super().__init__(token)
        self.tokensAndParamExpressions = []#array of tokens and Expressions
        self.parenType = parenType
        #self.callSuper = False
        self.procDef = None# the proc def of the base function (won't point to overrides)
        self.procDefThatIsExecuted = None#if the original proc def gets overrided, then this will point to the 
        #proc def that is the last override (or if it's a super call it will point to the second to last proc def in the chain)
        self.syntaxType = PROCCALL

        self.paramExpressions = []
        
    def getInputPattern(self, uppercase = True):
        inputPattern = ""
        for i in range(len(self.tokensAndParamExpressions)):
            if isinstance(self.tokensAndParamExpressions[i], tokenize.Token):
                inputPattern += self.tokensAndParamExpressions[i].tokenData
            else:
                inputPattern += "_"

        
        return inputPattern.upper() if uppercase else inputPattern
    def finalInit(self, allProcedures, allOpenEndedProcCalls, problems):
        inputPattern = self.getInputPattern()
        if inputPattern in allProcedures:
            self.procDef = allProcedures[inputPattern]
            
        else:
            if inputPattern in allOpenEndedProcCalls:
                allOpenEndedProcCalls[inputPattern].append(self)
            else:
                allOpenEndedProcCalls[inputPattern] = [self]

        for tpe in self.tokensAndParamExpressions:
            if isinstance(tpe, Expression):
                self.paramExpressions.append(tpe)

class Output(Syntax):#Return functionality
    def __init__(self, token):
        super().__init__(token)
        self.expression = None
        self.syntaxType = OUTPUT
        

def isVariableIdentifier(tokenStr):
    return tokenStr[0] in tokenize.symbolsInIdentifier and tokenStr[0] not in tokenize.numbers and tokenStr not in keywords

def build_ast(tokens, problems=None):
    activeVariables = {}
    ast = []
    activeVariables["*allProcedures"] = {}
    activeVariables["*allOpenEndedProcCalls"] = {}
    activeVariables["*numLocalVars"] = 0
    activeVariables["*numGlobalVars"] = 0

    seenProcDefYet = [False]

    r = 0
    while r < len(tokens) and r != -1:
        
        if len(tokens[r][0].tokenData) == 0:
            if len(tokens[r]) > 1:
                if tokens[r][1].type == tokenize.NEWFILE:
                    seenProcDefYet.append(False)
                    r += 1
                elif tokens[r][1].type == tokenize.ENDNEWFILE:
                    del seenProcDefYet[-1]
                    r += 1
                else:
                    previousR = r
                    lineOfCode, r, typeOfLine = parseLineOfCode(tokens, activeVariables, r, True, problems)
                    ast.append(lineOfCode)

                    if typeOfLine == PROCDEF:
                        seenProcDefYet[-1] = True
                    elif typeOfLine == VARSET:
                        if seenProcDefYet[-1]:
                            TokProblem("In each file, global variable assignments cannot be below any procedure definitions. FIX: Move variable '" + tokens[previousR][1].tokenData + "' above all the other procedure definitions in the file", tokens[previousR][1], problems)
                            return ast, activeVariables
                
                
            else:
                #Problem("How?", tokens[r][0].file, tokens[r][0].lineNumber, tokens[r][0].index, problems=problems)
                pass
    if len(problems) == 0:
        for key in activeVariables["*allOpenEndedProcCalls"]:
            for procCall in activeVariables["*allOpenEndedProcCalls"][key]:
                TokProblem("There is an attempt to execute a procedure here with the input pattern '" + procCall.getInputPattern(False).replace("_","(INPUT)") + "' but none of the procedure definitions match", procCall.startToken, problems)
    
    return ast, activeVariables


def parseLineOfCode(tokens, activeVariables, r, isGlobal, problems):
    typeOfLine = None
    c = None
    if tokens[r][1].tokenData == procDefinitionKeyword or tokens[r][1].tokenData == procOverrideKeyword or tokens[r][1].tokenData == exemptKeyword:
        ret, r = parseProcDef(tokens, activeVariables, r, problems)
        typeOfLine = PROCDEF
    elif tokens[r][1].type == tokenize.OPEN_PAREN:
        ret, c = parseProcCall(tokens[r], activeVariables, 1, isGlobal, problems)
        typeOfLine = PROCCALL
    elif tokens[r][1].tokenData == globalKeyword or (tokens[r][1].type == tokenize.IDENTIFIER and len(tokens[r]) > 3 and (tokens[r][2].tokenData == "=" or tokens[r][2].tokenData == "'s")):
        ret, c = parseVarSet(tokens, activeVariables, r, 1, isGlobal, problems)
        typeOfLine = VARSET
    elif tokens[r][1].tokenData == forEachKeyword:
        ret, r = parseForEach(tokens, activeVariables, r, 1, isGlobal, problems)
        typeOfLine = FOREACH
    elif tokens[r][1].tokenData == ifKeyword:
        ret, r = parseIf(tokens, activeVariables, r, 1, isGlobal, problems)
        typeOfLine = IF
    elif tokens[r][1].tokenData == tryKeyword:
        ret, r = parseTry(tokens, activeVariables, r, 1, isGlobal, problems)
        typeOfLine = TRY
    elif isGlobal == False and tokens[r][1].tokenData == returnKeyword:
        ret, c = parseReturn(tokens, activeVariables, r, 1, problems)
        typeOfLine = OUTPUT
    else:
        TokProblem("Cannot parse this line of code", tokens[r][1], problems)
        return None, -1, None


    if c == None: 
        return ret, r, typeOfLine
    else:
        if c == -1:
            return ret, r+1, typeOfLine
        if c < len(tokens[r]): 
            TokProblem("Line of code has ended, so there may not be any more code past this point", tokens[r][c], problems)
            return ret, r+1, typeOfLine
        else:
            return ret, r + 1, typeOfLine
def parseReturn(tokens, activeVariables, r, c, problems):
    if tokens[r][c].tokenData != returnKeyword:
        TokProblem("'output statement' must begin with " + returnKeyword, tokens[r][c], problems)
    ret = Output(tokens[r][c])
    if not (c + 1 < len(tokens[r])):
        return ret, c+1
    retExpression, c = parseExpression(tokens[r], activeVariables, c+1, False, problems)
    ret.expression = retExpression
    return ret,c
def parseTry(tokens, activeVariables, r, c, isGlobal, problems):
    if tokens[r][c].tokenData != tryKeyword:
        TokProblem("'try statement' must begin with " + ifKeyword, tokens[r][c], problems)
    if c+1 < len(tokens[r]):
        TokProblem("'try statement' header has already finished. No code can exist on the same line after the header is finished. Code inside the 'try statement' must be on the next line below with an extra indent.", tokens[r][c], problems)



    ret = Try(tokens[r][c])

    blockCode, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)
    ret.code = blockCode

    if r >= len(tokens): return ret, r
    if len(tokens[r]) <= 1 or tokens[r][1].tokenData != catchKeyword: return ret, r

    if len(tokens[r]) <= 2:
        TokProblem("After the 'catch' keyword, there must be a variable name. The varible will store the error to be caught", tokens[r][1], problems)
        return None, r+1
    if tokens[r][2].type != tokenize.IDENTIFIER:
        TokProblem("After the 'catch' keyword, there must be a variable name. The varible will store the error to be caught", tokens[r][2], problems)
        return None, r+1
    varName = tokens[r][2].tokenData

    catch = Catch(tokens[r][1])
    catch.varName = varName
    catch.varType = GLOBAL_VARIABLE if isGlobal else LOCAL_VARIABLE

    ret.catch = catch



    registerVariableSet(activeVariables, varName, catch, isGlobal, False, tokens[r][2], problems)

    catchBlock, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)


    catch.code = catchBlock

    return ret,r

def parseIf(tokens, activeVariables, r, c, isGlobal, problems):
    if tokens[r][c].tokenData != ifKeyword:
        TokProblem("'if statement' must begin with " + ifKeyword, tokens[r][c], problems)
    if c+1 >= len(tokens[r]):
        TokProblem("The 'if' keyword must be followed by an expression that evaluates to either true (or @true) or false (or @false)"  , tokens[r][c], problems)
    ret = If(tokens[r][c])
    ifExpression, c = parseExpression(tokens[r], activeVariables, c+1, isGlobal, problems)
    if c < len(tokens[r]):
        TokProblem("'if statement' header has already finished. No code can exist on the same line after the header is finished. Code inside the 'if statement' must be on the next line below with an extra indent.", tokens[r][c], problems)
    
    ret.ifTestExpression = ifExpression

    blockCode, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)
    ret.code = blockCode


    previousIfOrElif = ret

    while r < len(tokens):
        if tokens[r][1].tokenData == elseKeyword:
            if 2 < len(tokens[r]):
                TokProblem("No code can be written on the same line after the 'else' keyword", tokens[r][2], problems)
            elseStatement = Else(tokens[r][1])
            blockCode, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)
            elseStatement.code = blockCode
            previousIfOrElif.elseBlock = elseStatement
            break
        elif tokens[r][1].tokenData == elifKeyword:
            if 2 >= len(tokens[r]):
                TokProblem("After the 'elif' there needs to be a code expression which is the condition for this 'else if'", tokens[r][1], problems)
            ifExpression, c = parseExpression(tokens[r], activeVariables, 2, isGlobal, problems)
            if c < len(tokens[r]):
                TokProblem("'elif statement' header has already finished. No code can exist on the same line after the header is finished. Code inside the 'elif statement' must be on the next line below with an extra indent.", tokens[r][c], problems)
            
            elifStatement = If(tokens[r][1])
            elifStatement.ifTestExpression = ifExpression
            blockCode, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)
            elifStatement.code = blockCode
            previousIfOrElif.elifBlock = elifStatement
            previousIfOrElif = elifStatement
            continue
        break
    return ret, r


def parseForEach(tokens, activeVariables, r, c, isGlobal, problems):
    if tokens[r][c].tokenData != forEachKeyword:
        TokProblem("For-each loop must begin with " + forEachKeyword, tokens[r][c], problems)
        return None, -1
    if not(c + 3 < len(tokens[r])):
        TokProblem("For-each loop must look like this: " + forEachKeyword + " <<insert variable name>> in <<some list or other iterable>>", tokens[r][c], problems)
        return None, -1
    if tokens[r][c+1].type != tokenize.IDENTIFIER:
        TokProblem("For-each loop must look like this: " + forEachKeyword + " <<insert variable name>> in <<some list or other iterable>>. The variable name is not valid.", tokens[r][c+1], problems)
        return None, -1
    varname = tokens[r][c+1].tokenData
    ret = ForEach(tokens[r][c])


    registerVariableSet(activeVariables, varname, ret, isGlobal, False, tokens[r][c+1], problems)


    if tokens[r][c+2].tokenData != "in":
        TokProblem("For-each loop must look like this: " + forEachKeyword + " <<insert variable name>> in <<some list or other iterable>>. The 'in' keyword is missing.", tokens[r][c+2], problems)
        return None, -1
    iteratorExpression, c = parseExpression(tokens[r], activeVariables, c+3, isGlobal, problems)
    if c < len(tokens[r]):
        TokProblem("For-each header has already finished. No code can exist on the same line after the header is finished. Code inside the loop must be on the next line below with an extra indent.", tokens[r][c], problems)

    ret.iteratorExpression = iteratorExpression
    blockCode, r = parseBlock(tokens, activeVariables, r, isGlobal, problems)
    ret.code = blockCode

    ret.finalInit(activeVariables["*allProcedures"], activeVariables["*allOpenEndedProcCalls"], problems)
    return ret, r 

def parseVarAccess(tokens, activeVariables, c, isGlobal, problems):
    accessGlobalVarInsideFunction = False
    if tokens[c].tokenData == globalKeyword:
        if isGlobal:
            TokProblem("You do not need to use '" + globalKeyword + "' to access global variables when in global scope", tokens[c], problems)
        else:
            accessGlobalVarInsideFunction = True
        if c+1 >= len(tokens):
            TokProblem("'" + globalKeyword + "' must be followed by a global variable name", tokens[c], problems)
            return None, c + 1
        c += 1
    
    if tokens[c].type != tokenize.IDENTIFIER: 
        TokProblem("Variable set must start with the name of the variable, then followed by the euqal sign", tokens[c], problems)
        return None, c+1
    varname = ("#" if (isGlobal or accessGlobalVarInsideFunction) else "") + tokens[c].tokenData

    VARNAME = varname.upper()
    #if VARNAME not in activeVariables:
    #    VARNAME = "#" + VARNAME
    if VARNAME not in activeVariables:
        TokProblem("Trying to access variable '" + str(tokens[c].tokenData) + "' but there is no variable of that name", tokens[c], problems)
        return None, c + 1

    #print(VARNAME, "is in", activeVariables.keys())

    ret = VarAccess(tokens[c], varname)

    ret.varID = activeVariables[VARNAME].varID
    ret.isConstantVariableAccess = activeVariables[VARNAME].isConstant
    ret.varType = GLOBAL_VARIABLE if (isGlobal or accessGlobalVarInsideFunction) else LOCAL_VARIABLE


    while c+1 < len(tokens):
        if tokens[c + 1].tokenData == "'s":
            if ret.apostrophe_s_VarNames == None: ret.apostrophe_s_VarNames = []
        else:
            break
        c += 2
        if c < len(tokens):
            ret.apostrophe_s_VarNames.append(tokens[c])
        else:
            Problem("\"'s\" must be followed by a variable name", tokens[c-1], problems)
    c += 1
    return ret, c
def parseExpression(tokens, activeVariables, c, isGlobal, problems):
    if tokens[c].type == tokenize.OPEN_PAREN or tokens[c].tokenData == superKeyword:
        return parseProcCall(tokens, activeVariables, c, isGlobal, problems)
    elif tokens[c].type == tokenize.IDENTIFIER or tokens[c].tokenData == globalKeyword:
        return parseVarAccess(tokens, activeVariables, c, isGlobal, problems)
    elif tokens[c].type == tokenize.NUMBER:
        return Literal(tokens[c], tokens[c].tokenData), c+1
    elif tokens[c].type == tokenize.QUOTE:
        return Literal(tokens[c], tokens[c].tokenData), c+1
    else:
        
        TokProblem("Invalid code", tokens[c], problems)
        return None, c+1
def registerVariableSet(activeVariables, name, syntaxObj, isGlobal, accessGlobalVarInsideFunction, variableNameToken, problems):
    syntaxObj.varName = name
    isGlobal = isGlobal or accessGlobalVarInsideFunction
    syntaxObj.varType = GLOBAL_VARIABLE if isGlobal else LOCAL_VARIABLE
    if isGlobal and not name.startswith("#"):
        name = "#"+name

    NAME = name.upper()


    if not isGlobal:
        if NAME not in activeVariables:
            activeVariables[NAME] = syntaxObj
            syntaxObj.varID = activeVariables["*numLocalVars"]
            activeVariables["*numLocalVars"] += 1
        else:
            syntaxObj.varID = activeVariables[NAME].varID
    elif isGlobal and accessGlobalVarInsideFunction:
        if NAME not in activeVariables:
            TokProblem("Global variable with the name " + name[1:] + " has not been declared anywhere above.", variableNameToken, problems)
        else:
            #modify the existing global variable
            syntaxObj.varID = activeVariables[NAME].varID
            if activeVariables[NAME].isConstant:
                TokProblem("'" + name[1:] + "' is a constant. Cannot change the value of a constant", syntaxObj.startToken, problems)

            #TODO
    elif isGlobal:
        #create new global variable
        activeVariables[NAME] = syntaxObj
        syntaxObj.varID = activeVariables["*numGlobalVars"]
        activeVariables["*numGlobalVars"] += 1
    


def parseVarSet(tokens, activeVariables, r, c, isGlobal, problems):
    accessGlobalVarInsideFunction = False
    if tokens[r][c].tokenData == globalKeyword:
        if isGlobal:
            TokProblem("You do not need to use '" + globalKeyword + "' to access global variables when in global scope", tokens[r][c], problems)
        else:
            accessGlobalVarInsideFunction = True
        if c+1 >= len(tokens[r]):
            TokProblem("'" + globalKeyword + "' must be followed by a global variable name", tokens[r][c], problems)
            return None, -1
        c += 1
    if tokens[r][c].type != tokenize.IDENTIFIER or not(c+2 < len(tokens[r])): 
        TokProblem("Variable set must must look like this:" + (" global" if accessGlobalVarInsideFunction else "" ) +" <<variable name>> = <<some value>>", tokens[r][c], problems)
        
        return None, -1
    varname = ("#" if (isGlobal or accessGlobalVarInsideFunction) else "") + tokens[r][c].tokenData
    if tokens[r][c + 1].tokenData == "=": 
        ret = VarSet(tokens[r][c], varName=varname, type=None)

        #registerVariableSet(activeVariables, varname, ret, isGlobal, accessGlobalVarInsideFunction, tokens[r][c], problems)
        
        if tokens[r][c+2].tokenData == "=":
            indexOfExpression = c+3
            ret.isConstant = True
            if not isGlobal:
                TokProblem("Cannot set variable using '==' inside a procedure. '==' can only be used with global variables to make them constants", tokens[r][c+1], problems)
        else:
            indexOfExpression = c+2
        

        varValue, endColumn = parseExpression(tokens[r], activeVariables, indexOfExpression, isGlobal, problems)
        registerVariableSet(activeVariables, varname, ret, isGlobal, accessGlobalVarInsideFunction, tokens[r][c], problems)
        ret.expression = varValue

        #print(activeVariables)
        

        return ret, endColumn
    elif tokens[r][c + 1].tokenData == "'s":
        ret = VarSet(tokens[r][c], varName=varname, type=GLOBAL_VARIABLE if (isGlobal or accessGlobalVarInsideFunction) else LOCAL_VARIABLE)

        if varname.upper() not in activeVariables:
            TokProblem(("Global variable " if (isGlobal or accessGlobalVarInsideFunction) else "Variable ") + (varname if not varname.startswith("#") else varname[1:]) + " does not exist", tokens[r][c], problems)
        
        ret.varID = activeVariables[varname.upper()].varID
        ret.apostrophe_s_VarNames = []
        
        while True:
            c += 2


            if not(c < len(tokens[r])):
                TokProblem("After the \"'s\" there needs to be a variable/field name and then an equal sign, and then a value", tokens[r][c], problems)
                return None, r+1
            if tokens[r][c].type != tokenize.IDENTIFIER: 
                TokProblem("After the \"'s\" there needs to be a variable/field name", tokens[r][c], problems)
                return None, r+1
            
            varname = tokens[r][c].tokenData
            ret.apostrophe_s_VarNames.append(tokens[r][c])

            if tokens[r][c + 1].tokenData == "'s":
                continue
            elif tokens[r][c + 1].tokenData == "=":




                varValue, c = parseExpression(tokens[r], activeVariables, c+2, isGlobal, problems)
                ret.expression = varValue
                
                return ret, c
            else:
                TokProblem("After the \"'s\" there needs to be a variable/field name and then an equal sign, and then a value", tokens[r][c+1], problems)
                return None, -1

    else:
        TokProblem("Variable set must start with the name of the variable, then followed by the euqal sign", tokens[r][c+1], problems)
        return None, -1

#this doesn't work for proc calls spanning multiple linesPROBBBBBBBBBBBBLLLLLLLLLLLLLLEEEEEEEEEEEEEMMMMMMMMMMMMMMMMMHERE
def parseProcCall(tokens, activeVariables, c, isGlobal, problems):
    """
    callSuper = False
    if tokens[c].tokenData == superKeyword:
        callSuper = True
        c += 1
        if c >= len(tokens):
            TokProblem("After the 'super' keyword, there must be a procedure call inside a pair of parenthesis", tokens[c-1], problems)
    """
        
    if tokens[c].type != tokenize.OPEN_PAREN: TokProblem("Function call doesn't beigin with open parenthesis", tokens[c], problems)
    if tokens[c+2].type != tokenize.CLOSE_PAREN: TokProblem("Function call doesn't end with close parenthesis", tokens[c+2], problems)
    procType = tokens[c].tokenData
    ret = ProcCall(tokens[c], procType)
    #ret.callSuper = callSuper
    innerTokens = tokens[c + 1]
    if not isinstance(innerTokens.tokenData, list): TokProblem("Must be list of tokens inside function call", innerTokens, problems)

    innerIndex = 0
    while innerIndex < len(innerTokens.tokenData):
        tok = innerTokens.tokenData[innerIndex]

        if ((tok.type == tokenize.IDENTIFIER or tok.type == tokenize.SINGLE_SYMBOL_IDENTIFIER) and tok.tokenData.upper() not in activeVariables) or tok.tokenData == "*":
            
            #part of the procedure name
            ret.tokensAndParamExpressions.append(tok)
            innerIndex += 1
        else:
            #it's inputting a value as a parameter to the proc
            innerExpression, innerIndex = parseExpression(innerTokens.tokenData, activeVariables, innerIndex, isGlobal, problems)
            
            ret.tokensAndParamExpressions.append(innerExpression)
        
            
    ret.finalInit(activeVariables["*allProcedures"], activeVariables["*allOpenEndedProcCalls"], problems)
    
    return ret, c + 3



#return "w" or "p" to be added to pattern  
def registerProcedureParam(procDef, sigWithOnlyIdentifiers, activeVariables, typeToken, paramNameToken, problems):
    if paramNameToken.type != tokenize.IDENTIFIER:
        TokProblem("Parameter name can only contain letters and numbers and it can't be a keyword, so it can't be '" + str(paramNameToken.tokenData) + "'", paramNameToken, problems)
    sigWithOnlyIdentifiers.append(paramNameToken)
    ret = "p"
    

    varName = paramNameToken.tokenData
    param = Param(paramNameToken, varName)
    param.varType = LOCAL_VARIABLE
    param.inputDatatypeToken = typeToken
    param.inputDatatype = types.dataTypeSymbolToTypes[typeToken.tokenData]

    VARNAME = varName.upper()
    
    if VARNAME in activeVariables and (activeVariables[VARNAME].varType == LOCAL_VARIABLE):
        TokProblem("There are two parameters called '" + varName + "'", paramNameToken, problems)
    else:
        if VARNAME not in activeVariables:
            activeVariables[VARNAME] = param
            param.varID = activeVariables["*numLocalVars"]
            activeVariables["*numLocalVars"] += 1
    procDef.params.append(param)
    return ret

def parseProcDef(tokens, activeVariables, r, problems):
    funcTitleNumTokens = len(tokens[r])
    if funcTitleNumTokens < 2:
        
        Problem("Procedure definition incorrect", tokens[r][0].file, tokens[r][0].lineNumber, tokens[r][0].index, problems=problems)
    indent = len(tokens[r][0].tokenData)
    if indent > 0: Problem("Procedure definition cannot start with an indent", tokens[r][0].file, tokens[r][0].lineNumber, tokens[r][0].index, problems=problems)
    


    procSignatureStart = 2
    procDefinitionIndex = 1
    isExempt = False
    if tokens[r][1].tokenData == exemptKeyword:
        procSignatureStart = 3
        procDefinitionIndex = 2
        isExempt = True


    if tokens[r][procDefinitionIndex].tokenData == procDefinitionKeyword:
        ret = ProcDef(tokens[r][procDefinitionIndex], False)
    elif tokens[r][1].tokenData == procOverrideKeyword:
        ret = ProcDef(tokens[r][procDefinitionIndex], True)
    else:
        TokProblem("Procedure definition incorrect", tokens[r][1], problems)
        return None, -1
    if isExempt:
        ret.exemptFromChecks = True
    if funcTitleNumTokens != procSignatureStart+3 and funcTitleNumTokens != procSignatureStart+5:
        
        Problem("Procedure definition incorrect", tokens[r][1].file, tokens[r][1].lineNumber, tokens[r][1].index, problems=problems)
        return None, -1
    ret.procSignature = tokens[r][procSignatureStart:]
    
        
    
        

    open = ret.procSignature[0]
    close = ret.procSignature[2]
    if open.tokenData not in tokenize.opensSet:
        Problem("Procedure input pattern must start with either '(' or '{' or '[' or '<', not " + str(open.tokenData), open.file, open.lineNumber, open.index, problems=problems)
        return None, -1
    correctClosingSymbol = tokenize.closes[tokenize.openCloseIndex[open.tokenData]]
    if close.tokenData != correctClosingSymbol:
        Problem("Procedure header must close with" + correctClosingSymbol + ", not " + str(close.tokenData), close.file, close.lineNumber, close.index, problems=problems)
        return None, -1
    if len(ret.procSignature) == 5:
        if ret.procSignature[3].tokenData == "no" and (ret.procSignature[4].tokenData == "output" or ret.procSignature[4].tokenData == "outputs"):
            ret.fToken = ret.procSignature[4]
            ret.returnType = types.VOID
        elif ret.procSignature[3].tokenData == "outputs":
            if ret.procSignature[4].tokenData in tokenize.typeSymbols:
                ret.returnTypeToken = ret.procSignature[4]
                ret.returnType = types.dataTypeSymbolToTypes[ret.procSignature[4].tokenData]
            else:
                TokProblem("After the 'output' keyword, there must be a type symbol ('&' for list, '#' for number, '^' for string, ':' for object, '*' for any) or there can be the phrse 'no output'. Cannot have '" + str(ret.procSignature[4].tokenData) + "'", inside.tokenData[i], problems)
        else:
            TokProblem("After the function header, there must be the keyword 'output' followed by a type symbol ('&' for list, '#' for number, '^' for string, ':' for object, '*' for any) or there can be the phrse 'no output'. Cannot have '" + str(ret.procSignature[3].tokenData) + "'", inside.tokenData[i], problems)
    elif len(ret.procSignature) == 3:
        ret.returnTypeToken = None
        ret.returnType = None
    else:
        TokProblem("Procedure definition incorrect", open, problems)



    pattern = ""
    sigWithOnlyIdentifiers = []

    inside = ret.procSignature[1]
    if not inside.type == tokenize.INSIDE_PAREN: 
        Problem("??? this shouldnt happen" + str(inside.tokenData), inside.file, inside.lineNumber, inside.index, problems=problems)
    i = 0
    while i < len(inside.tokenData):
        if inside.tokenData[i].type == tokenize.SINGLE_SYMBOL_IDENTIFIER or inside.tokenData[i].type == tokenize.SPECIAL_CHAR:
            if inside.tokenData[i].tokenData in tokenize.typeSymbols:

                if i+1 >= len(inside.tokenData) or inside.tokenData[i+1].tokenData in tokenize.typeSymbols:
                    if inside.tokenData[i].tokenData in "*":
                        sigWithOnlyIdentifiers.append(inside.tokenData[i])
                        pattern += "w"
                        i += 1
                    else:
                        TokProblem("Cannot have " + inside.tokenData[i].tokenData + " in procedure header unless it is specifying the type of a parameter", inside.tokenData[i], problems)
                        i += 1
                else:
                    pattern +=  registerProcedureParam(ret, sigWithOnlyIdentifiers, activeVariables, inside.tokenData[i], inside.tokenData[i+1], problems)

                    i += 2
            elif inside.tokenData[i].type == tokenize.SINGLE_SYMBOL_IDENTIFIER:
                sigWithOnlyIdentifiers.append(inside.tokenData[i])
                pattern += "w"
                i += 1
            else:
                TokProblem("Cannot use  '" + inside.tokenData[i].tokenData + "' in procedure header at this position token is" + inside.tokenData[i].tokenData, inside.tokenData[i], problems)
                i += 1

        elif inside.tokenData[i].type == tokenize.IDENTIFIER:


            #if i+1 < len(inside.tokenData) and inside.tokenData[i+1].tokenData == "..":
            #    pattern += registerProcedureParam(ret, sigWithOnlyIdentifiers, activeVariables, inside.tokenData[i+1], inside.tokenData[i], problems)
            #    i += 2
            #else:
            if True:
                sigWithOnlyIdentifiers.append(inside.tokenData[i])
                pattern += "w"
                i += 1
        else:
            TokProblem("Each input of the procedure must have '*' followed by <name of input>. Invalid token '" + str(inside.tokenData[i].tokenData) + "'",inside.tokenData[i+1], problems)
            i += 1



    ret.pattern = pattern
    ret.procSignatureWithoutStarsOrParen = sigWithOnlyIdentifiers
    ret.numParams = pattern.count("p")


    functionCode, r = parseBlock(tokens, activeVariables, r, False, problems)
    ret.code = functionCode

    ret.finalInit(activeVariables["*allProcedures"], activeVariables["*allOpenEndedProcCalls"], problems)

    for key in list(activeVariables.keys()):
        if isinstance(activeVariables[key], Syntax):
            if activeVariables[key].varType == LOCAL_VARIABLE:
                del activeVariables[key]
    ret.numLocalVars = activeVariables["*numLocalVars"]
    activeVariables["*numLocalVars"] = 0
    return ret, r
def parseBlock(tokens, activeVariables, rowOfBlockHeader, isGlobal, problems):
    blockCode = []
    blockHeaderIndent = getIndentLevel(tokens[rowOfBlockHeader][0], problems)
    r = rowOfBlockHeader + 1
    while r < len(tokens) and r != -1:
        if getIndentLevel(tokens[r][0], problems) <= blockHeaderIndent: break

        lineOfCode, r, _ = parseLineOfCode(tokens, activeVariables, r, isGlobal, problems)
        blockCode.append(lineOfCode)
    return blockCode, r


def getIndentLevel(indentToken, problems):
    if indentToken.type != tokenize.INDENT:
        TokProblem("First token not indent", indentToken, problems)
    return int(len(indentToken.tokenData)/glass.tabSize)

def printActiveVariables(av):
    for key in av:
        if not key.startswith("*"):
            print(key, ":", av[key])