
from email.quoprimime import quote
import sys
import os

from numpy import number
import glass
Problem = glass.Problem
import build_ast
from itertools import chain

includeComments = False





IDENTIFIER = 0
OPEN_PAREN = 1
CLOSE_PAREN = 2
QUOTE = 3
COMMENT = 4
SPECIAL_CHAR = 5
SINGLE_SYMBOL_IDENTIFIER = 6
INSIDE_PAREN = 7
INDENT = 8
NUMBER = 9
KEYWORD = 10
NEWFILE = 11
ENDNEWFILE = 12

artificiallyAddedLines = [

    "copy __GlassStdLib.gl"
]


class Token:
    def __init__(self, tokenData, file, lineNumber, index=None, endIndex=None, problems=None):
        self.tokenData = tokenData
        self.file = file
        self.lineNumber = lineNumber
        self.index = index if index != None else endIndex - len(tokenData)

        self.type = self.findType(problems)

    def __repr__(self):
        return repr(self.tokenData)
    def __str__(self):
        return "Tok(" + repr(self.tokenData) + ", " + str(self.type) + ")"
    def findType(self, problems):
        tokenData = self.tokenData
        if isinstance(tokenData, list):
            return INSIDE_PAREN
        elif tokenData.strip() == "":
            return INDENT

        
        elif tokenData[0] in symbolsInIdentifier and tokenData[0] not in numbers and ('.' not in tokenData[0]):
            if tokenData not in build_ast.keywords:
                return IDENTIFIER
            else:
                return KEYWORD
        elif len(tokenData) == 1 and tokenData[0] in singleCharacterIdentifiers:
            return SINGLE_SYMBOL_IDENTIFIER
        elif len(tokenData) == 1 and tokenData[0] in opensSet:
            return OPEN_PAREN
        elif len(tokenData) == 1 and tokenData[0] in closesSet:
            return CLOSE_PAREN
        elif tokenData[0] == "\"":
            self.tokenData = eval(tokenData)
            return QUOTE
        elif len(tokenData) >= 6 and tokenData[0:3] == "'''":
            return COMMENT
        elif tokenData in specialChars.union({"'s"}):
            return SPECIAL_CHAR
        elif tokenData[0] in symbolsInNumber:
            try:
                self.tokenData = int(tokenData)
            except:
                try:
                    self.tokenData = float(tokenData)
                except:
                    glass.TokProblem("Cannot interpret " + str(tokenData) + " as a value", self, problems)
            return NUMBER
        elif tokenData == "~":
            return NEWFILE
        elif tokenData == "~~":
            return ENDNEWFILE
        

        


opensSet = {'(', '{', '[', '<'}
closesSet = {')', '}', ']', '>'}
opens = ['(', '{', '[', '<']
closes = [')', '}', ']', '>']
openCloseIndex = {
                    '(' : 0, ')' : 0,
                    '{' : 1, '}' : 1,
                    '[' : 2, ']' : 2,
                    '<' : 3, '>' : 3,
                    }

numbers = [str(i) for i in range(10)]

singleCharacterIdentifiers = {'+', '-', '/', '|', '%', '!',',',";"}

symbolsInIdentifier = {"."}
for i in range(65, 65+26):
    symbolsInIdentifier.add(chr(i))
for i in range(97, 97+26):
    symbolsInIdentifier.add(chr(i))
for i in range(0,10):
    symbolsInIdentifier.add(str(i))


otherSymbols = {"\"","\n"," ","'"}#symbols that are allowed but don't mean anything

typeSymbols = {"^","#","&",":","*","?"}
specialChars = {"=","@"}.union(typeSymbols)

allAllowedSymbols = opensSet.union(closesSet).union(singleCharacterIdentifiers).union(symbolsInIdentifier).union(otherSymbols).union(specialChars)

symbolsInNumber = {"."}
for i in range(0,10):
    symbolsInNumber.add(str(i))


def tokenizeAndCopy(file, filesSeen, problems=None, doNotCopyStdLib = False):
    if not file.endswith(".gl"):
        Problem(file + " does not end with '" + glass.glassFileExtension +"'", problems=problems)
        quit()
    if file in filesSeen:
        return []
        #Problem(file + " has a copy instruction which eventually results in copying itself. The copied version of itself also has a copy instruction to copy itself (because it's the same file). This results in an infinite loop.", problems=problems)
        #quit()
    filesSeen.append(file)
    tokenizedFile = []

    if not os.path.isfile(file):
        Problem("The file \"" + file + "\" does not exist", problems=problems)
        quit()
    f = open(file, "r")


    identifierStart = -1
    parenthesis = []

    lineNumber = 0

    commentStart = -1
    openingDotsInARow = 0
    closingDotsinARow = 0
    commentText = ""
    quoteStart = -1
    quoteText = ""
    lineTokenized = [[]]
    
    
    if os.path.basename(file) != "__GlassStdLib.gl":
        lineNumber -= len(artificiallyAddedLines)
        fileIterator = chain(artificiallyAddedLines, f)
    else:
        fileIterator = f
    onlySpacesSoFar = True
    spacesAtBeginning = 0
    for line in fileIterator:
        if not line.endswith("\n"): line = line + "\n"
        
        



        for i in range(len(line)):
            
            #if file == "test.gl": print(line[i], lineTokenized)
            if quoteStart == -1 and commentStart == -1:

                #start quote
                if line[i] == '"':
                    quoteStart = (i,lineNumber)
                    continue
                #start comment
                if openingDotsInARow >= 3 and line[i] != '\'':
                    commentStart = (i - openingDotsInARow, lineNumber)
                    quoteStart = -1
                    identifierStart = -1
                    continue

                else:
                    if line[i] == '\'':
                        openingDotsInARow += 1
                    else:
                        openingDotsInARow = 0

                if len(parenthesis) == 0:
                    if onlySpacesSoFar:
                        if line[i] != ' ':
                            onlySpacesSoFar = False
                            lineTokenized[-1].append(Token(spacesAtBeginning*" ", file, lineNumber, endIndex=i, problems=problems))
                        elif line[i] == ' ':
                            spacesAtBeginning += 1
                else:
                    onlySpacesSoFar = False
                if line[i] not in allAllowedSymbols:
                    Problem("'" + line[i] + "' is an illegal character", file=file, line=lineNumber, index=i, problems=problems)

                #add identifier to tokens (find end of identifier)
                
                        
                #startDoubleDot = line[i] == "." and i+1 < len(line) and line[i+1] == "."
                #endDoubleDot = line[i] != "." and i-1 >= 0 and line[i-1] == "." and i-2 >= 0 and line[i-2] == "."
                #if identifierStart != -1 and (line[i] not in symbolsInIdentifier or (startDoubleDot or endDoubleDot) ):
                if identifierStart != -1 and line[i] not in symbolsInIdentifier:
                    t = Token(line[identifierStart : i], file, lineNumber, identifierStart, problems=problems)
                    #do the copy statement
                    if identifierStart == 0 and t.tokenData == "copy":
                        fileToCopy = line[i:]
                        fileToCopy = fileToCopy.strip()
                        fileToCopy = os.path.join(os.path.dirname(file), fileToCopy)
                        tokenizedFile = tokenizedFile + [[Token("",fileToCopy,0,0), Token("~",fileToCopy,0,0)]] + tokenizeAndCopy(fileToCopy, filesSeen, problems=problems, doNotCopyStdLib = True) + [[Token("",fileToCopy,0,0), Token("~~",fileToCopy,0,0)]]
                        identifierStart = -1
                        break
                    lineTokenized[-1].append(t)

                    #if endDoubleDot:
                    #    lineTokenized[-1].append(Token("..", file, lineNumber, endIndex=i, problems=problems))
                            
                    




                    identifierStart = -1

                #find open paren
                if line[i] in opens:
                    parenthesis.append(line[i])
                    lineTokenized[-1].append(Token(line[i], file, lineNumber, i, problems=problems))
                    lineTokenized.append([])
                #close off paren
                elif line[i] in closes:
                    closeSymbol = line[i]
                    openSymbol = opens[openCloseIndex[closeSymbol]]
                    if len(parenthesis) == 0:
                        Problem("There's a closing '" + closeSymbol + "' without there previously being a '" + openSymbol + "'", file, lineNumber, i, problems=problems)
                    elif parenthesis[-1] != openSymbol:
                        Problem("There's a closing '" + closeSymbol + "' but previously there was a '" + parenthesis[-1] + "' which is a different type", file, lineNumber, i, problems=problems)
                    else:
                        del parenthesis[-1]
                        lineTokenized[-2].append(Token(lineTokenized[-1], file, lineNumber, i, problems=problems))
                        del lineTokenized[-1]
                        lineTokenized[-1].append(Token(line[i], file, lineNumber, i, problems=problems))

                
                apostropheS = False
                #start identifier
                if identifierStart == -1:

                    if line[i] == "s" and i > 0 and line[i-1] == "'":
                        lineTokenized[-1].append(Token("'s", file, lineNumber, endIndex=i+1, problems=problems))
                        apostropheS = True
                    elif line[i] in symbolsInIdentifier:
                        identifierStart = i
                    elif line[i] in singleCharacterIdentifiers:
                        lineTokenized[-1].append(Token(line[i], file, lineNumber, i, problems=problems))
                    elif line[i] == "'" and (i+2 < len(line) and line[i+2] != "'") and (i > 0 and line[i-1] != "'") and not (line[i-1] != "'" and line[i+1] != "'"):
                        Problem("Invalid use of apostrophes", file, lineNumber, index=i, problems=problems)
                    

                #add special character tokens (like equal sign)
                if line[i] in specialChars and not apostropheS: lineTokenized[-1].append(Token(line[i], file, lineNumber, i, problems=problems))
                



                
                
                
            else:
                #end quote
                if quoteStart != -1 and line[i] == '"' and (i == 0 or (line[i-1] != "\\")):
                    if quoteText != "":
                        quoteText += line[0:i+1]
                        quoteText = quoteText.replace("\n","\\n")
                        lineTokenized[-1].append(Token(quoteText, file, quoteStart[1], quoteStart[0], problems=problems))
                        quoteText = ""
                        
                    else:
                        lineTokenized[-1].append(Token(line[quoteStart[0]:i+1], file, lineNumber, quoteStart[0], problems=problems))
                    quoteStart = -1
                        
                    
                #end comment
                if commentStart != -1:
                    if line[i] == '\'':
                        closingDotsinARow += 1
                    else:
                        closingDotsinARow = 0

                    if closingDotsinARow == openingDotsInARow:
                        
                        if commentText != "":
                            commentText += line[0:i+1]
                            
                            if includeComments: lineTokenized[-1].append(Token(commentText, file, commentStart[1], commentStart[0], problems=problems))
                            #print("Comment:",commentText)
                            commentText = ""
                        else:
                            if includeComments: lineTokenized[-1].append(Token(line[commentStart[0]:i+1], file, lineNumber, commentStart[0], problems=problems))
                            #print("Comment:",line[commentStart[0]:i+1])
                        closingDotsinARow = 0
                        openingDotsInARow = 0
                        commentStart = -1

        
            
                
        
        if quoteStart != -1:
            quoteText += line[quoteStart[0]:]
            quoteStart = 0,quoteStart[1]
        if commentStart != -1:
            commentText += line[commentStart[0]:]
            #print("Comment text", commentText)
            commentStart = 0,commentStart[1]
        #if len(parenthesis) > 0:
        #    Problem("There needs to be another " + parenthesis[-1] + "".join([" and another " + parenthesis[i] for i in range(-2, -len(parenthesis), -1)]),file, lineNumber, i-1)
        
        if quoteStart == -1 and commentStart == -1 and len(parenthesis) == 0:
            if len(lineTokenized[0]) > 1:
                tokenizedFile.append(lineTokenized[0])
            lineTokenized[0] = []

            onlySpacesSoFar = True
            spacesAtBeginning = 0
        

        lineNumber += 1

        
    if quoteStart != -1:
        Problem("There needs to be another '\"' to close the quote",file, quoteStart[1], quoteStart[0], problems=problems)
    if commentStart != -1:
        Problem("The comment is not closed",file, commentStart[1], commentStart[0], problems=problems)



    #del filesSeen[-1]
    return tokenizedFile


