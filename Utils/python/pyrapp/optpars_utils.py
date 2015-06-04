import json
import csv

# -----------------------------------------------------------------------------------------------------------
class ScratchAppend:
    def __init__(self,typ=str):
        self.cold = True
        self.typ = typ
        
    def __call__(self,option, opt_str, value, parser, *args, **kwargs):
        target = getattr(parser.values,option.dest)
        if self.cold:
            del target[:]
            self.cold = False
        if type(value) == str and "," in value:
            for v in value.split(","):
                target.append(self.typ(v))
        else:
            target.append(self.typ(value))
                                                    
# -----------------------------------------------------------------------------
class Load:
    def __init__(self,scratch=False,empty={}):
        self.cold = True
        self.scratch = scratch
        self.empty = empty
    
    def __call__(self,option, opt_str, value, parser, *args, **kwargs):
        if self.scratch and self.cold:
            setattr(parser.values,option.dest,self.empty)
            self.cold = False
            
        if option.dest == "__opts__":
            dest = parser.values
        else:
            dest = getattr(parser.values,option.dest)
        
            
        if type(dest) == dict:
            setter = dict.__setitem__
            getter = dict.get
        else:
            setter = setattr
            getter = getattr
        
        for cfg in value.split(","):
            cf = open(cfg)
            settings = json.loads(cf.read())
            for k,v in settings.iteritems():
                attr  = getter(dest,k,None)
                if attr and type(attr) == list:           
                    attr.extend(v)
                setter(dest,k,v)
            cf.close()

# -----------------------------------------------------------------------------
class Csv:
    def __call__(self,option, opt_str, value, parser, *args, **kwargs):
        dest = getattr(parser.values,option.dest)
        if not dest:
            setattr(parser.values,option.dest,[])
            dest = getattr(parser.values,option.dest)
        cf = open(value)
        reader = csv.DictReader(cf)
        for row in reader:
            dest.append(row)            
        cf.close()
        