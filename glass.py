
import sys
import os

import atexit
import sys



#foreach line in file




import shutil

tabSize = 4
glassFileExtension = ".gl"
glassStdLibPrototype = "./GlassStdLibPrototype.gl"
MAX_RECURSION_DEPTH = 700







problems = []
def main():
    sys.setrecursionlimit(MAX_RECURSION_DEPTH*10)
    global problems
    args = sys.argv
    if len(args) <= 1:
        Problem("No commanmd line args received. Try typing \"glass TheNameOfYourFile.gl\"", problems=problems)
        quit()
    
    fileName = args[1]
    
    commandLineArgs = args[2:]
    shutil.copy(glassStdLibPrototype, "./__GlassStdLib.gl")
    masterFile = tokenize.tokenizeAndCopy(fileName,[],problems=problems)
    
    if len(problems) > 0: quit()
    #for s in masterFile:
    #    print(s)
    #quit()

    syntaxTree, allVars = build_ast.build_ast(masterFile,problems=problems)

    if len(problems) > 0: quit()

    ast_check.checkProcTiers(syntaxTree, allVars, problems)
    #print((allVars))
    if len(problems) > 0: quit()
    #print("\n\n\n")
    #for s in syntaxTree:
    #    print(s)
    
    interpreter.run(syntaxTree, allVars, commandLineArgs)


def TokProblem(msg, token, problems, autoStr = True):
    return Problem(msg, token.file, token.lineNumber, token.index, problems=problems, token=token, autoStr=autoStr)



verboseErrors = False
class Problem:
    def __init__(self, msg, file=None, line=None, index=None, problems=None, token=None, autoStr = True):
        self.msg = msg
        self.file = file
        self.line = line
        self.index = index
        self.token=token
        self.autoStr = autoStr
        problems.append(self)
    def __str__(self):
        if not self.autoStr:
            return self.msg
        verbose = ""
        if self.token != None and verboseErrors:
            verbose = " -> " + str(self.token)


        codePointer = ""
        try:
            f = open(self.file,"r")
            i = 0
            for line in f:
                if self.line == i:
                    codePointer = "\n" + (line if line.endswith("\n") else line + "\n")
                    break
                i += 1

            codePointerMsg = "Error Here"
            codePointerMsgIndex = self.index - int(len(codePointerMsg)/2)
            if codePointerMsgIndex < 0: codePointerMsgIndex = 0
            codePointer += " " * self.index + "^" + "\n" + " " * (codePointerMsgIndex) + codePointerMsg
            
        except Exception as e:
            pass
        if self.file != None and self.line != None and self.index != None:
            #return "ERROR: " + self.msg + "... In file" + self.file + " at line " + str(self.line+1) + " at position " + str(self.index+1) + verbose + codePointer
            return "ERROR: " + self.msg + "... In file '" + self.file + "' at line " + str(self.line+1) + " at position " + str(self.index+1) + ":" + verbose + codePointer
        else:
            return "ERROR: " + self.msg + verbose + codePointer
            
def onExit():
    probs = list(problems)
    probs.reverse()

    if len(probs) > 0:
        if len(probs) > 1:
            print("\n*******CANNOT START PROGRAM DUE TO " + str(len(probs)) + " ISSUES******\n")
        else:
            print("\n*******CANNOT START PROGRAM DUE TO " + str(len(probs)) + " ISSUE******\n")
        for problem in probs:
            print(problem)
            print()
    
atexit.register(onExit)
import glasstokenize as tokenize
import build_ast
import interpreter
import ast_check
if __name__ == "__main__": main()