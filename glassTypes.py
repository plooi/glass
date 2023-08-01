















class SpecialObject:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name


VOID = object()#the return type of a procedure that returns void
EMPTY = SpecialObject("EMPTY")#variable can be assigned EMPTY which means it points to an invalid memory location (like null)
NORETURNVAL = SpecialObject("VOID(IMPLICIT)")#expressions that simply dont even attempt to return anything will return NORETURNVAL ()
VOIDVALUE = SpecialObject("VOID(EXPLICIT)")#procedures that explicitly are declared no output and explicitly output EMPTY or just "output" will return VOIDVALUE

class GlassObject:
    def __init__(self):
        self.data = {}
        self.constant = None#if assigned to a constant global variable, self.constant will take on the varset syntax
    def __repr__(self):
        return str(self.data)
class GlassException(GlassObject,Exception):
    def __init__(self):
        super().__init__()

class GlassList(GlassObject):
    def __init__(self):
        super().__init__()
        self.data["LIST"] = []

dataTypeSymbolToTypes = {"^" : (str, None), "#" : (int, float), "*" : None, ":" : (GlassObject, GlassException), "&" : (GlassList, None), "?" : (bool, None)}


def typeToTypeName(t):
    if t == int or t == float or t == (int, float):
        typeName = "number(#)"
    elif t == bool or t == (bool, None):
        typeName = "boolean(?)"
    elif t == str or t == (str, None):
        typeName = "text(^)"
    elif t == GlassList or t == (GlassList, None):
        typeName = "list(&)"
    elif t == GlassObject or t == GlassException or t == (GlassObject, GlassException):
        typeName = "object(:)"
    elif t == None:
        typeName = "anything(*)"
    elif t == VOID:
        typeName = "no-output"
    else:
        typeName = "Unknown Type"
    return typeName 