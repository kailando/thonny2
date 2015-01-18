# -*- coding: utf-8 -*-
 
"""
Classes used both by front-end and back-end
"""
import shlex

class Record:
    def __init__(self, **kw):
        self.__dict__.update(kw)
    
    def update(self, **kw):
        self.__dict__.update(kw)
    
    def setdefault(self, **kw):
        "updates those fields that are not yet present (similar to dict.setdefault)"
        for key in kw:
            if not hasattr(self, key):
                setattr(self, key, kw[key])
    
    def __repr__(self):
        keys = self.__dict__.keys()
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(self.__class__.__name__, ", ".join(items))
    
    def __str__(self):
        keys = sorted(self.__dict__.keys())
        items = ("{}={!r}".format(k, str(self.__dict__[k])) for k in keys)
        return "{}({})".format(self.__class__.__name__, ", ".join(items))
    
    def __eq__(self, other):
        if type(self) != type(other):
            return False
        
        if len(self.__dict__) != len(other.__dict__):
            return False 
        
        for key in self.__dict__:
            if not hasattr(other, key):
                return False
            self_value = getattr(self, key)
            other_value = getattr(other, key)
            
            if type(self_value) != type(other_value) or self_value != other_value:
                return False
        
        return True

    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(repr(self))

class TextRange(Record):
    def __init__(self, lineno, col_offset, end_lineno, end_col_offset):
        self.lineno = lineno
        self.col_offset = col_offset
        self.end_lineno = end_lineno
        self.end_col_offset = end_col_offset
    
    def contains_smaller(self, other):
        return ((other.lineno > self.lineno
                 or other.lineno == self.lineno 
                    and other.col_offset > self.col_offset)
                and (other.end_lineno < self.end_lineno
                 or other.end_lineno == self.end_lineno 
                    and other.end_col_offset < self.end_col_offset))
    
    def contains_smaller_eq(self, other):
        return ((other.lineno > self.lineno
                 or other.lineno == self.lineno 
                    and other.col_offset >= self.col_offset)
                and (other.end_lineno < self.end_lineno
                 or other.end_lineno == self.end_lineno 
                    and other.end_col_offset <= self.end_col_offset))
    
    def not_smaller_in(self, other):
        return not other.contains_smaller(self)

    def is_smaller_in(self, other):
        return other.contains_smaller(self)
    
    def not_smaller_eq_in(self, other):
        return not other.contains_smaller_eq(self)

    def is_smaller_eq_in(self, other):
        return other.contains_smaller_eq(self)
    
    def get_start_index(self):
        return str(self.lineno) + "." + str(self.col_offset)
    
    def get_end_index(self):
        return str(self.end_lineno) + "." + str(self.end_col_offset)
    
    def __str__(self):
        return "TR(" + str(self.lineno) + "." + str(self.col_offset) + ", " \
                     + str(self.end_lineno) + "." + str(self.end_col_offset) + ")"
    
    
                 
class ValueInfo(Record):
    pass

class FrameInfo(Record):
    def get_description(self):
        return (
            "[" + str(self.id) + "] "
            + self.code_name + " in " + self.filename
            + ", focus=" + str(self.focus)
        )


"""
# I didn't bother listing possible cases and fields of CommunicationObjects
# but did't want to use dict either (object form is a bit nicer to write) 
class CommunicationObject:
    def __init__(self, **kw):
        for key in kw:
            if key.endswith("_range") and isinstance(kw[key], tuple):
                value = TextRange(*kw[key])
            else:
                value = kw[key]
                
            setattr(self, key, value)
    
    def serialize(self):
        d = self.__dict__.copy()
        d["class"] = self.__class__.__name__
        return repr(d)
    
    def __repr__(self):
        return self.serialize()
"""
class ActionCommand(Record):
    pass

class ToplevelCommand(ActionCommand):
    pass

class DebuggerCommand(ActionCommand):
    pass

class InlineCommand(Record):
    """
    Can be used both during debugging and between debugging.
    Initially meant for sending variable and heap info requests
    """
    pass

class InputSubmission(Record):
    pass


class PauseMessage(Record):
    "PauseMessage-s indicate that backend has paused and is waiting for new command"
    pass

class ActionResponse(PauseMessage):
    pass

class ToplevelResponse(ActionResponse):
    def __init__(self, **kw):
        kw["vm_state"] = "toplevel"
        Record.__init__(self, **kw)

class DebuggerResponse(ActionResponse):
    def __init__(self, **kw):
        kw["vm_state"] = "debug"
        Record.__init__(self, **kw)


class InlineResponse(Record):
    """
    Meant for getting variable/heap info from backend
    """


class InputRequest(PauseMessage):
    def __init__(self, **kw):
        kw["vm_state"] = "input"
        Record.__init__(self, **kw)

class OutputEvent(Record):
    pass


class CommandSyntaxError(Exception):
    pass

def serialize_message(msg):
    return repr(msg)

def parse_message(msg_string):
    return eval(msg_string)


def parse_shell_command(cmd_line):
    if cmd_line.startswith("%"):
        parts = shlex.split(cmd_line.strip(), posix=False)
        
        command = parts[0][1:]
        
        if command == "Reset":
            assert len(parts) == 1
            return ToplevelCommand(command="Reset")
        elif command == "cd":
            if len(parts) == 2:
                return ToplevelCommand(command="cd", path=unquote_path(parts[1]))
            elif len(parts) > 2:
                # extra flexibility for those who forget the quotes
                return ToplevelCommand(command="cd", 
                                       path=unquote_path(cmd_line.split(maxsplit=1)[1]))
        elif command.lower() in ("run", "debug"):
            if len(parts) > 2:
                raise CommandSyntaxError("Filename missing in '{0}'".format(cmd_line))
            return ToplevelCommand(command=command,
                                   filename=unquote_path(parts[1]),
                                   args=parts[2:])
        else:
            raise AssertionError("Unknown magic command: " + command)
        
    elif len(cmd_line.strip()) == 0:
        return ToplevelCommand(command="pass")
    else:
        return ToplevelCommand(command="python", cmd_line=cmd_line)


def quote_path_for_shell(path):
    # http://stackoverflow.com/a/25208652/261181
    try:
        from shlex import quote
    except ImportError:
        from pipes import quote
    
    return quote(path)

def unquote_path(path):
    # TODO: may be incomplete
    return path.strip("'").strip('"').replace("\\\\", "\\")


def print_structure(o):
    print(o.__class__.__name__)
    for attr in dir(o):
        print(attr, "=", getattr(o, attr))

if __name__ == "__main__":
    tr1 = TextRange(1,2,3,4)
    tr2 = TextRange(1,2,3,4)
    print(tr1 == tr2)