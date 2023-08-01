

from numpy import isin
import glass
import build_ast
import glasstokenize as tokenize
import glassTypes
from glassTypes import GlassException, GlassList, GlassObject


endLoop = glassTypes.SpecialObject("End Loop Object")



allProcedures = None
def run(syntaxTree, allVars, commandLineArgs):
    global allProcedures

    allProcedures = allVars["*allProcedures"]
    #print(allProcedures.keys())
    globalVars = [glassTypes.EMPTY]*allVars["*numGlobalVars"]
    stackTrace = []
    #print("all vars",allVars)
    #for key in allVars:
    #    print(":" + key)
    #    print(allVars[key])
    try:
        runCodeBlock(syntaxTree, globalVars, stackTrace, [])


        #run the start function
        runStartFunction = True
        if "START_" in allVars["*allProcedures"]:
            numParams = 1
            procDefToExecute = allVars["*allProcedures"]["START_"]
        elif "START" in allVars["*allProcedures"]:
            numParams = 0
            procDefToExecute = allVars["*allProcedures"]["START"]
        else:
            runStartFunction = False
        if runStartFunction:
            while procDefToExecute.overridedBy != None:
                procDefToExecute = procDefToExecute.overridedBy

            innerLocalVars = [glassTypes.EMPTY] * procDefToExecute.numLocalVars

            if numParams == 1:
                param = GlassList()
                param.data["LIST"] = commandLineArgs
                innerLocalVars[0] = param
                types = procDefToExecute.params[0].inputDatatype
                #print(types)
                if types != None and type(innerLocalVars[0]) != types[0] and type(innerLocalVars[0]) != types[1]:
                    throwGlassExceptionFromInterpreter("Parameter '" + procDefToExecute.params[0].name + "' *MUST* be a list(&) or anything(*)", stackTrace, procDefToExecute)
            
            codeToExecute = procDefToExecute.code

            stackTrace.append(procDefToExecute)
            try:
                ret = runCodeBlock(codeToExecute, globalVars, stackTrace, innerLocalVars)
                del stackTrace[-1]
                return ret
            except GlassException as ge:
                del stackTrace[-1]
                raise ge
    except GlassException as ge:
        print("\n\n***RUNTIME ERROR***\n")#, ge.glassObject.data["MESSAGE"])
        syntaxIndex = -1
        for syntax in ge.data["STACKTRACE"]:

            syntaxIndex += 1
            
            token = syntax.startToken
            try:
                if token.file != None:
                    
                    f = open(token.file,"r")
                    i = 0
                    for line in f:
                        if token.lineNumber == i:


                            line = (line[0:-1] if line.endswith("\n") else line)
                            spacesRemoved = 0
                            while line.startswith(" "):
                                line = line[1:]
                                spacesRemoved += 1


                            #errorMessage = "This line of code:\n" + (line[0:-1] if line.endswith("\n") else line) + "        (line " + str(token.lineNumber+1) + " of " + str(token.file) + ") "
                            #errorMessage =  "Line " + str(token.lineNumber+1) + " of " + str(token.file) + "\n" + (line[0:-1] if line.endswith("\n") else line) + "        "
                            starting = "Line " + str(token.lineNumber+1) + " of " + str(token.file) + "~~~~~~~~ "
                            errorMessage =  starting + (line[0:-1] if line.endswith("\n") else line) + " ~~~~~~~~"
                            

                            if syntaxIndex == len(ge.data["STACKTRACE"]) - 1:
                                errorMessage += "raising an error on the grounds that:" 
                            elif isinstance(syntax, build_ast.ProcDef):
                                errorMessage += "executed the procedure \"" + syntax.getFriendlyName() + "\" which led to"
                            elif isinstance(syntax, build_ast.ProcCall):
                                errorMessage += "executing the procedure \"" + syntax.procDefThatIsExecuted.getFriendlyName() + "\" which led to"



                            errorMessage += "\n"+ " " * (token.index - spacesRemoved + len(starting)) + "↑"#"^" 

                            if syntaxIndex == len(ge.data["STACKTRACE"]) - 1:
                                
                                errorMessageMsg = ge.data["MESSAGE"]
                                errorMessageMsgIndex = token.index - int(len(errorMessageMsg)/2) - spacesRemoved + len(starting)
                                if errorMessageMsgIndex < 0: errorMessageMsgIndex = 0
                                errorMessage += "\n" + " " * (errorMessageMsgIndex) + errorMessageMsg
                            
                            
                            print(errorMessage + "\n")
                            break
                            
                        i += 1
                    

                    
                else:
                    print("no file")

                
                
            except Exception as e:
                print(e)
        

def runCodeBlock(code, globalVars, stackTrace, localVars):
    global allProcedures
    for i in range(len(code)):
        line = code[i]
        #print("running line", str(line.startToken.lineNumber), "of", line.startToken.file)
        if line.syntaxType == build_ast.FOREACH:
            iterator = evalExpression(line.iteratorExpression, globalVars, stackTrace, localVars)

            if type(iterator) == GlassObject:
                if "CLASSES" in iterator.data and type(iterator.data["CLASSES"]) == GlassList and "iterator" in iterator.data["CLASSES"].data["LIST"]:
                    if "ITERATE_" not in allProcedures:
                        throwGlassExceptionFromInterpreter("There is no {iterate :obj} procedure. Cannot run 'foreach loop' without the {iterate :obj} procedure defined")

                    
                    procDefToExecute = allProcedures["ITERATE_"]


                    while procDefToExecute.overridedBy != None:
                        procDefToExecute = procDefToExecute.overridedBy
                    
                    if procDefToExecute.returnType == glassTypes.VOID:
                        throwGlassExceptionFromInterpreter("The {iterate :obj} procedure must have an output (cannot be 'no output')", stackTrace, procDefToExecute)
                    paramValues = None
                    
                    #keep repeating until you get "endLoop"
                    while True:
                        
                        #iterate through function overrides
                        while True:
                            #print("\n\n\n\n\n"+str(expressionSyntax))
                            innerLocalVars = [glassTypes.EMPTY] * procDefToExecute.numLocalVars
                            
                            #add the parameters
                            innerLocalVars[0] = iterator
                            
                            codeToExecute = procDefToExecute.code
                                
                            stackTrace.append(line)
                            try:
                                iterationValue = runCodeBlock(codeToExecute, globalVars, stackTrace, innerLocalVars)
                                #print(procDefToExecute.getFriendlyName(), "returned",ret)
                                
                                if iterationValue == glassTypes.NORETURNVAL:#if the function reaches the end without returning anything...
                                    if procDefToExecute.overrides != None:#if there's overrided functions, then do the overrided funcs next
                                        procDefToExecute = procDefToExecute.overrides
                                        #print("continue")
                                        continue
                                    elif procDefToExecute.returnType == None:#If we reached the end and there's no overrided functionst to do, but the return type is *, return glassTypes.EMPTY
                                        iterationValue = glassTypes.EMPTY
                                    elif procDefToExecute.returnType == glassTypes.VOID:
                                        #If we reached the end and there's no overrided functions, but it's also a void return type, then just return glassTypes.NORETURNVAL
                                        pass
                                    else:#we reached the end and there's no overrides, not * and not void return type, now we have a problem
                                        throwGlassExceptionFromInterpreter("This procedure promises to output a " + glassTypes.typeToTypeName(procDefToExecute.returnType) + " but when executing the procedure, no 'output' statement was reached", stackTrace, procDefToExecute.startToken)

                                
                                del stackTrace[-1]
                                #return ret
                                #check for end of loop

                                break
                            except GlassException as ge:
                                del stackTrace[-1]
                                raise ge
                        if iterationValue == endLoop:
                            break
                        setVar(line, iterationValue, globalVars, localVars)
                        maybeReturnValue = runCodeBlock(line.code, globalVars, stackTrace, localVars)
                        if maybeReturnValue != glassTypes.NORETURNVAL:
                            return maybeReturnValue
                else:
                    for key in iterator.data:
                        setVar(line, key, globalVars, localVars)
                        maybeReturnValue = runCodeBlock(line.code, globalVars, stackTrace, localVars)
                        if maybeReturnValue != glassTypes.NORETURNVAL:
                            return maybeReturnValue
            elif type(iterator) == GlassList:
                for key in iterator.data['LIST']:
                    setVar(line, key, globalVars, localVars)
                    maybeReturnValue = runCodeBlock(line.code, globalVars, stackTrace, localVars)
                    if maybeReturnValue != glassTypes.NORETURNVAL:
                        return maybeReturnValue
            else:
                throwGlassExceptionFromInterpreter("'" + str(iterator) + "' cannot be put into a foreach loop.", stackTrace, line.iteratorExpression)

        elif line.syntaxType == build_ast.IF:
            while True:
                ifTest = evalExpression(line.ifTestExpression, globalVars, stackTrace, localVars)
                if ifTest is True:
                    maybeReturnValue = runCodeBlock(line.code, globalVars, stackTrace, localVars)
                    if maybeReturnValue != glassTypes.NORETURNVAL:
                        return maybeReturnValue
                    break
                elif ifTest is False: 
                    if line.elifBlock != None:
                        line = line.elifBlock
                        continue
                    elif line.elseBlock != None:
                        maybeReturnValue = runCodeBlock(line.elseBlock.code, globalVars, stackTrace, localVars)
                        if maybeReturnValue != glassTypes.NORETURNVAL:
                            return maybeReturnValue

                else:
                    throwGlassExceptionFromInterpreter("The code after the if statement must evaluate to either true (or @true) or false (or @false), not '" + str(ifTest) + "'", stackTrace, line.ifTestExpression)
                break



        elif line.syntaxType == build_ast.TRY:
            try:
                maybeReturnValue = runCodeBlock(line.code, globalVars, stackTrace, localVars)
                if maybeReturnValue != glassTypes.NORETURNVAL:
                    return maybeReturnValue
            except GlassException as e:
                if line.catch != None:
                    localVars[line.catch.varID] = e.glassObject
                    maybeReturnValue = runCodeBlock(line.catch.code, globalVars, stackTrace, localVars)
                    if maybeReturnValue != glassTypes.NORETURNVAL:
                        return maybeReturnValue
        elif line.syntaxType == build_ast.VARSET:
            if line.apostrophe_s_VarNames != None:
                if line.varType == build_ast.GLOBAL_VARIABLE:
                    object = globalVars[line.varID]
                else:
                    object = localVars[line.varID]
                for j in range(len(line.apostrophe_s_VarNames)-1):
                    if type(object) != GlassObject and type(object) != GlassException:
                        if object == glassTypes.EMPTY:
                            throwGlassExceptionFromInterpreter("'s ".join([line.varName] + [t.tokenData for t in line.apostrophe_s_VarNames[:j]]) + " is empty, so it has no properties", stackTrace, line)
                        else:
                            throwGlassExceptionFromInterpreter("'s ".join([line.varName] + [t.tokenData for t in line.apostrophe_s_VarNames[:j]]) + " is not an object (it is a " + glassTypes.typeToTypeName(type(object)) +"), so it has no properties", stackTrace, line)

                    propertyName = line.apostrophe_s_VarNames[j].tokenData.upper()
                    if propertyName not in object.data:
                        throwGlassExceptionFromInterpreter("Cannot find property named '" + propertyName  + "' of the object " + str(object.data), stackTrace, line)
                    object = object.data[propertyName]
                if type(object) != GlassObject and type(object) != GlassException:
                    if object == glassTypes.EMPTY:
                        throwGlassExceptionFromInterpreter("'s ".join([line.varName] + [t.tokenData for t in line.apostrophe_s_VarNames[:-1]]) + " is empty, so it has no properties", stackTrace, line)
                    else:
                        throwGlassExceptionFromInterpreter("'s ".join([line.varName] + [t.tokenData for t in line.apostrophe_s_VarNames[:-1]]) + " is not an object (it is a " + glassTypes.typeToTypeName(type(object)) +"), so it has no properties", stackTrace, line)
                propertyName = line.apostrophe_s_VarNames[-1].tokenData.upper()
                value = evalExpression(line.expression, globalVars, stackTrace, localVars)
                if value == glassTypes.NORETURNVAL or value == glassTypes.VOIDVALUE:
                    throwGlassExceptionFromInterpreter("Expression doesn't output anything. Glass cannot set a variable to a value that doesn't exist. Most likely the procedure called here has 'no output' specified as its output type" + str(object.data), stackTrace, line)
                object.data[propertyName] = value
                
            else:
                val = evalExpression(line.expression, globalVars, stackTrace, localVars)
                if val == glassTypes.NORETURNVAL or val == glassTypes.VOIDVALUE:
                    throwGlassExceptionFromInterpreter("Code is trying to set the value of variable '" + line.varName + "', but the expression on the right hand side of the equal sign does not output anything", stackTrace, line.expression)
                setVar(line, val, globalVars, localVars)
        elif line.syntaxType == build_ast.PROCCALL:
            evalExpression(line, globalVars, stackTrace, localVars)
        elif line.syntaxType == build_ast.OUTPUT:
            ret = glassTypes.EMPTY
            if line.expression != None:
                ret = evalExpression(line.expression, globalVars, stackTrace, localVars)

            if len(stackTrace) == 0:
                throwGlassExceptionFromInterpreter("Cannot output from global area", stackTrace, line)
            #print("\n\n\n\n" + str(stackTrace[-1].procDefThatIsExecuted))
            parentProcDef = stackTrace[-1].procDefThatIsExecuted
            acceptableTypes = parentProcDef.returnType
            if acceptableTypes == glassTypes.VOID:
                if ret == glassTypes.EMPTY:
                    return glassTypes.VOIDVALUE
                else:
                    throwGlassExceptionFromInterpreter("The function '" + parentProcDef.getFriendlyName() + "' has 'no output' but an attempt was made to try to output something from this function", stackTrace, line)
            elif acceptableTypes == None:
                return ret
            else:
                if type(ret) in acceptableTypes:
                    return ret
                else:
                    throwGlassExceptionFromInterpreter("The function '" + parentProcDef.getFriendlyName() + "' must output a " + glassTypes.typeToTypeName(acceptableTypes) + " but the code tries to output a " + glassTypes.typeToTypeName (type(ret)), stackTrace, line.expression)




    return glassTypes.NORETURNVAL

            
def makeConstant(obj, constantVariableSyntax):
    if isinstance(obj, glassTypes.GlassObject) and obj.constant == None:
        obj.constant = constantVariableSyntax
        for key in obj.data:
            makeConstant(obj.data[key], constantVariableSyntax)

def setVar(syntaxWithVarSetFunctionality, value, globalVars, localVars):
    
    if syntaxWithVarSetFunctionality.varType == build_ast.GLOBAL_VARIABLE:
        if syntaxWithVarSetFunctionality.isConstant:
            if isinstance(value, glassTypes.GlassObject):
                makeConstant(value, syntaxWithVarSetFunctionality)
        globalVars[syntaxWithVarSetFunctionality.varID] = value

    else:
        localVars[syntaxWithVarSetFunctionality.varID] = value


    
def evalExpression(expressionSyntax, globalVars, stackTrace, localVars):
    if expressionSyntax.syntaxType == build_ast.PROCCALL:
        
        if len(stackTrace) >= glass.MAX_RECURSION_DEPTH:
            throwGlassExceptionFromInterpreter("Maximum recursion depth exceeded (max recursion depth is " + str(glass.MAX_RECURSION_DEPTH) + ")", stackTrace, expressionSyntax)
        procDefToExecute = expressionSyntax.procDefThatIsExecuted
        #print("EXECUTE", procDefToExecute.header)
        paramValues = None
        while True:
            #print("\n\n\n\n\n"+str(expressionSyntax))
            innerLocalVars = [glassTypes.EMPTY] * procDefToExecute.numLocalVars
            

            if paramValues != None:
                for i in range(len(expressionSyntax.paramExpressions)):
                    innerLocalVars[i] = paramValues[i]
            else:
                if procDefToExecute.overrides == None:
                    #print("No overrides ", procDefToExecute.getFriendlyName())
                
                    
                    for i in range(len(expressionSyntax.paramExpressions)):
                        innerLocalVars[i] = evalExpression(expressionSyntax.paramExpressions[i], globalVars, stackTrace, localVars)
                        types= procDefToExecute.params[i].inputDatatype
                        if types != None and type(innerLocalVars[i]) != types[0] and type(innerLocalVars[i]) != types[1]:
                            throwGlassExceptionFromInterpreter("Parameter '" + procDefToExecute.params[i].name + "' must be a " + glassTypes.typeToTypeName(types) + ", however a value of '" + str(innerLocalVars[i]) + "' was received, which is a " + glassTypes.typeToTypeName(type(innerLocalVars[i])), stackTrace, expressionSyntax.paramExpressions[i])
                        

                else:
                    #print("Has overrides ", procDefToExecute.getFriendlyName())
                    paramValues = [glassTypes.EMPTY] * len(expressionSyntax.paramExpressions)
                    for i in range(len(expressionSyntax.paramExpressions)):
                        innerLocalVars[i] = evalExpression(expressionSyntax.paramExpressions[i], globalVars, stackTrace, localVars)
                        paramValues[i] = innerLocalVars[i]
                        types= procDefToExecute.params[i].inputDatatype
                        if types != None and type(innerLocalVars[i]) != types[0] and type(innerLocalVars[i]) != types[1]:
                            throwGlassExceptionFromInterpreter("Parameter '" + procDefToExecute.params[i].name + "' must be a " + glassTypes.typeToTypeName(types) + ", however a value of '" + str(innerLocalVars[i]) + "' was received, which is a " + glassTypes.typeToTypeName(type(innerLocalVars[i])), stackTrace, expressionSyntax.paramExpressions[i])
                        
            codeToExecute = procDefToExecute.code


            if procDefToExecute.header == "+++COMMAND+TABLE+++____":
                fn = innerLocalVars[0]
                arg1 = innerLocalVars[1]
                arg2 = innerLocalVars[2]
                arg3 = innerLocalVars[3]
                #print("local vars", innerLocalVars)

                return commandTable(fn, arg1, arg2, arg3, stackTrace, expressionSyntax)
                
            else:
                stackTrace.append(expressionSyntax)
                try:
                    ret = runCodeBlock(codeToExecute, globalVars, stackTrace, innerLocalVars)
                    #print(procDefToExecute.getFriendlyName(), "returned",ret)

                    if ret == glassTypes.NORETURNVAL:#if the function reaches the end without returning anything...
                        if procDefToExecute.overrides != None:#if there's overrided functions, then do the overrided funcs next
                            procDefToExecute = procDefToExecute.overrides
                            #print("continue")
                            continue
                        elif procDefToExecute.returnType == None:#If we reached the end and there's no overrided functionst to do, but the return type is *, return glassTypes.EMPTY
                            ret = glassTypes.EMPTY
                        elif procDefToExecute.returnType == glassTypes.VOID:
                            #If we reached the end and there's no overrided functions, but it's also a void return type, then just return glassTypes.NORETURNVAL
                            pass
                        else:#we reached the end and there's no overrides, not * and not void return type, now we have a problem
                            throwGlassExceptionFromInterpreter("This procedure promises to output a " + glassTypes.typeToTypeName(procDefToExecute.returnType) + " but when executing the procedure, no 'output' statement was reached", stackTrace, procDefToExecute.startToken)

                    
                    del stackTrace[-1]
                    return ret
                except GlassException as ge:
                    del stackTrace[-1]
                    raise ge
            
    elif expressionSyntax.syntaxType == build_ast.VARACCESS:


        if expressionSyntax.apostrophe_s_VarNames != None:
            if expressionSyntax.varType == build_ast.GLOBAL_VARIABLE:
                object = globalVars[expressionSyntax.varID]
            else:
                object = localVars[expressionSyntax.varID]
            
            for j in range(len(expressionSyntax.apostrophe_s_VarNames)-1):

                if type(object) != GlassObject and type(object) != GlassException:
                    if object == glassTypes.EMPTY:
                        throwGlassExceptionFromInterpreter("'s ".join([expressionSyntax.varName] + [t.tokenData for t in expressionSyntax.apostrophe_s_VarNames[:j]]) + " is empty, so it has no properties", stackTrace, expressionSyntax)
                    else:
                        throwGlassExceptionFromInterpreter("'s ".join([expressionSyntax.varName] + [t.tokenData for t in expressionSyntax.apostrophe_s_VarNames[:j]]) + " is not an object (it is a " + glassTypes.typeToTypeName(type(object)) +"), so it has no properties", stackTrace, expressionSyntax)


                propertyName = expressionSyntax.apostrophe_s_VarNames[j].tokenData.upper()
                if propertyName not in object.data:
                    throwGlassExceptionFromInterpreter("Cannot find property named '" + propertyName  + "' of the object " + str(object.data), stackTrace, expressionSyntax)
                object = object.data[propertyName]


            if type(object) != GlassObject and type(object) != GlassException:
                if object == glassTypes.EMPTY:
                    throwGlassExceptionFromInterpreter("'s ".join([expressionSyntax.varName] + [t.tokenData for t in expressionSyntax.apostrophe_s_VarNames[:-1]]) + " is empty, so it has no properties", stackTrace, expressionSyntax)
                else:
                    throwGlassExceptionFromInterpreter("'s ".join([expressionSyntax.varName] + [t.tokenData for t in expressionSyntax.apostrophe_s_VarNames[:-1]]) + " is not an object (it is a " + glassTypes.typeToTypeName(type(object)) +"), so it has no properties", stackTrace, expressionSyntax)
            propertyName = expressionSyntax.apostrophe_s_VarNames[-1].tokenData.upper()
            if propertyName not in object.data:
                throwGlassExceptionFromInterpreter("Cannot find property named '" + propertyName  + "' of the object " + str(object.data), stackTrace, expressionSyntax)


            return object.data[propertyName]
        else:
            if expressionSyntax.varType == build_ast.GLOBAL_VARIABLE:
                #print("getting global variable", expressionSyntax.varName,"which has index",expressionSyntax.varID,"value is", globalVars[expressionSyntax.varID])
                return globalVars[expressionSyntax.varID]
            else:
                #print("getting local variable", expressionSyntax.varName,"which has index",expressionSyntax.varID,"value is", localVars[expressionSyntax.varID])
                
                return localVars[expressionSyntax.varID]
    elif expressionSyntax.syntaxType == build_ast.LITERAL:
        return expressionSyntax.literalValue
    else:
        print("Damn")
        quit()


def throwGlassExceptionFromInterpreter(message, stackTrace, syntax):
    e = GlassException()
    e.data["MESSAGE"] = message
    st = list(stackTrace)
    if syntax != None:
        st.append(syntax)
    e.data["STACKTRACE"] = st
    raise e
        

def commandTable(fn, arg1, arg2, arg3, stackTrace, syntax):
    if fn == 0:#print arg1
        print(arg1)
    elif fn == 1:#+
        return arg1 + arg2
    elif fn == 2:#-
        return arg1 - arg2
    elif fn == 3:#*
        return arg1 * arg2
    elif fn == 4:#/
        return arg1 / arg2
    elif fn == 5:#new object
        return GlassObject()
    elif fn == 6:#new exception
        ret = GlassException()
        return ret
    elif fn == 7:#raise exception arg1
        if "STACKTRACE" not in arg1.data:
            st = list(stackTrace)
            #st.append(syntax)
            arg1.data["STACKTRACE"] = st
        raise arg1
    elif fn == 8:#new list
        ret = GlassList()
        return ret
    elif fn == 9:#list access
        return arg1.data["LIST"][arg2]
    elif fn == 10:#list set
        if arg1.constant != None:throwGlassExceptionFromInterpreter("Tried to modify a list related to the constant global variable '" + arg1.constant.varName[1:] + "' in file " + str(arg1.constant.startToken.file) + " at line " + str(arg1.constant.startToken.lineNumber+1) + ". Cannot modify variables/objects that are constant.", stackTrace, None)
        arg1.data["LIST"][arg2] = arg3
    elif fn == 11:#add to list
        if arg1.constant != None:throwGlassExceptionFromInterpreter("Tried to modify a list related to the constant global variable '" + arg1.constant.varName[1:] + "' in file " + str(arg1.constant.startToken.file) + " at line " + str(arg1.constant.startToken.lineNumber+1) + ". Cannot modify variables/objects that are constant.", stackTrace, None)
        arg1.data["LIST"].append(arg2)
    elif fn == 12:#dictionary set
        if arg1.constant != None:throwGlassExceptionFromInterpreter("Tried to modify an object related to the constant global variable '" + arg1.constant.varName[1:] + "' in file " + str(arg1.constant.startToken.file) + " at line " + str(arg1.constant.startToken.lineNumber+1) + ". Cannot modify variables/objects that are constant.", stackTrace, None)
        arg1.data[arg2] = arg3
    elif fn == 13:#dictionary get
        return arg1.data[arg2]
    elif fn == 14:#str upper
        return arg1.upper()
    elif fn == 15:#str lower
        return arg1.lower()
    elif fn == 16:#substring
        return arg1.substring(arg2, arg3)
    elif fn == 17:#get NULL
        return glassTypes.EMPTY
    elif fn == 18:#soft equals
        return arg1 == arg2
    elif fn == 19:#greater than
        return arg1 > arg2
    elif fn == 20:#hard equals
        return arg1 is arg2
    elif fn == 21:#is number
        return type(arg1) == int or type(arg1) == float
    elif fn == 22:#is string
        return type(arg1) == str
    elif fn == 23:#is list
        return type(arg1) == GlassList
    elif fn == 24:#is object
        return type(arg1) == GlassObject
    elif fn == 25:#is exception
        return type(arg1) == GlassException
    elif fn == 32:#is boolean
        return type(arg1) == bool
    elif fn == 26:#arg1 in arg2.data (arg2 is GlassObject)
        return arg1 in arg2.data
    elif fn == 27:
        return True
    elif fn == 28:
        return False
    elif fn == 29:#length of object
        return len(arg1.data.keys())
    elif fn == 30:#length of list
        return len(arg1.data['LIST'])
    elif fn == 31:#stringify
        typ = type(arg1)
        if typ == int or typ == float or typ == str or typ == bool:
            return str(arg1)
    elif fn == 33:#join lists
        return arg1.data['LIST'] + arg2.data['LIST']
    elif fn == 34:#join objects
        ret = GlassObject()
        ret.data = {**arg1.data, **arg2.data}
        return ret
    elif fn == 35:#get endLoop
        return endLoop
    elif fn == 36:#arg1 in GlassList(arg2)
        return arg1 in arg2.data['LIST']
    

    

    return glassTypes.EMPTY