import json
from typing import Any, Dict, List, Union

class ExecutionTrace:
    def __init__(self):
        self.steps=[]; self.variables={}; self.output=[]; self.step_count=0
    def add_step(self, operation, details=None):
        self.step_count += 1
        details = details or {}
        self.steps.append({"step":self.step_count,"operation":operation,"timestamp":len(self.steps),"variables_before":dict(self.variables),**details,"variables_after":dict(self.variables)})
    def to_dict(self):
        return {"total_steps":self.step_count,"steps":self.steps,"final_variables":dict(self.variables),"output":list(self.output)}

class ProgramInterpreter:
    MAX_ITERATIONS=1000
    def __init__(self):
        self.trace=ExecutionTrace(); self.classes={}; self.objects={}; self.total_iterations=0
    def execute_ir(self, ir_json: Union[str,Dict[str,Any]]):
        try:
            ir=json.loads(ir_json) if isinstance(ir_json,str) else ir_json
            if not isinstance(ir,dict) or 'steps' not in ir: raise ValueError("IR must contain 'steps' key")
            self._execute_steps(ir['steps'])
        except Exception as e:
            self.trace.add_step('ERROR',{'error':str(e)})
        return self.trace.to_dict()
    def _execute_steps(self, steps):
        for step in steps:
            op=step.get('operation','').upper()
            if op=='SET': self._set(step)
            elif op in ('ADD','SUBTRACT','MULTIPLY','DIVIDE','MODULO'): self._update(step,op)
            elif op=='TYPECAST': self._typecast(step)
            elif op=='PRINT': self._print(step)
            elif op=='IF': self._if(step)
            elif op=='REPEAT': self._repeat(step)
            elif op=='FOR': self._for(step)
            elif op=='WHILE': self._while(step)
            elif op=='CLASS': self._class(step)
            elif op=='INHERIT': self._inherit(step)
            elif op=='OBJECT': self._object(step)
            elif op=='CALL_METHOD': self._call_method(step)
            elif op=='TRY_EXCEPT': self._try_except(step)
            elif op=='RAISE': self._raise(step)
            else: raise ValueError(f"Unknown operation: {op}")
    def _value(self,v):
        if isinstance(v,dict):
            if 'variable' in v and len(v)==1:
                name=v['variable']
                if name not in self.trace.variables: raise ValueError(f"Variable '{name}' not defined")
                return self.trace.variables[name]
            typ=v.get('type')
            if typ=='arithmetic':
                a,b=self._value(v['left']),self._value(v['right']); op=v['operator']
                if op=='+': return a+b
                if op=='-': return a-b
                if op=='*': return a*b
                if op=='/':
                    if b==0: raise ValueError('Division by zero')
                    return a/b
                if op=='%':
                    if b==0: raise ValueError('Modulo by zero')
                    return a%b
            if typ=='comparison': return self._compare(v['operator'],self._value(v['left']),self._value(v['right']))
            if typ=='logical':
                if v['operator']=='not': return not bool(self._value(v['value']))
                a=bool(self._value(v['left'])); b=bool(self._value(v['right']))
                return a and b if v['operator']=='and' else a or b
        return v
    def _compare(self,op,a,b):
        return {'>':a>b,'<':a<b,'>=':a>=b,'<=':a<=b,'==':a==b,'!=':a!=b}[op]
    def _set(self,s):
        name=s.get('variable');
        if not name: raise ValueError('SET requires a variable')
        val=self._value(s.get('value')); self.trace.variables[name]=val
        self.trace.add_step('SET',{'variable':name,'value':val})
    def _update(self,s,op):
        name=s.get('variable')
        if name not in self.trace.variables: raise ValueError(f"Variable '{name}' not defined")
        old=self.trace.variables[name]; x=self._value(s.get('value'))
        if op=='ADD': new=old+x
        elif op=='SUBTRACT': new=old-x
        elif op=='MULTIPLY': new=old*x
        elif op=='DIVIDE':
            if x==0: raise ValueError('Division by zero')
            new=old/x
        else:
            if x==0: raise ValueError('Modulo by zero')
            new=old%x
        self.trace.variables[name]=new; self.trace.add_step(op,{'variable':name,'operand':x,'old_value':old,'new_value':new})
    def _typecast(self,s):
        name=s.get('variable'); typ=s.get('target_type','').lower()
        if name not in self.trace.variables: raise ValueError(f"Variable '{name}' not defined")
        old=self.trace.variables[name]
        if typ in ('int','integer'): new=int(old)
        elif typ in ('float','decimal'): new=float(old)
        elif typ in ('str','string'): new=str(old)
        elif typ in ('bool','boolean'):
            if isinstance(old,str): new=old.strip().lower() in ('true','1','yes')
            else: new=bool(old)
        else: raise ValueError(f"Unsupported typecast: {typ}")
        self.trace.variables[name]=new; self.trace.add_step('TYPECAST',{'variable':name,'from':type(old).__name__,'to':typ,'value':new})
    def _print(self,s):
        value=self._value(s.get('value',s.get('message',''))); out=str(value)
        self.trace.output.append(out); self.trace.add_step('PRINT',{'output':out,'variables_at_print':dict(self.trace.variables)})
    def _if(self,s):
        result=bool(self._value(s['condition'])); self.trace.add_step('IF',{'condition':s['condition'],'result':result,'variables_at_check':dict(self.trace.variables)})
        if result: self._execute_steps(s.get('body',[])); return
        for e in s.get('elif',[]):
            r=bool(self._value(e['condition'])); self.trace.add_step('ELIF',{'condition':e['condition'],'result':r,'variables_at_check':dict(self.trace.variables)})
            if r: self._execute_steps(e.get('body',[])); return
        self._execute_steps(s.get('else_body',[]))
    def _repeat(self,s):
        times=int(self._value(s.get('times',0)))
        if times<0 or times>self.MAX_ITERATIONS: raise ValueError(f"Loop exceeds max iterations ({self.MAX_ITERATIONS})")
        for i in range(times):
            self.total_iterations+=1; self.trace.add_step('REPEAT',{'iteration':i+1,'total_iterations':times}); self._execute_steps(s.get('body',[]))
    def _for(self,s):
        start=int(self._value(s['start'])); end=int(self._value(s['end'])); count=0
        if end-start+1>self.MAX_ITERATIONS: raise ValueError(f"Loop exceeds max iterations ({self.MAX_ITERATIONS})")
        for i in range(start,end+1):
            count+=1; self.trace.variables[s['variable']]=i; self.trace.add_step('FOR',{'variable':s['variable'],'iteration':count,'value':i}); self._execute_steps(s.get('body',[]))
    def _while(self,s):
        count=0
        while bool(self._value(s['condition'])):
            count+=1
            if count>self.MAX_ITERATIONS: raise ValueError(f"WHILE loop exceeds max iterations ({self.MAX_ITERATIONS})")
            self.trace.add_step('WHILE',{'iteration':count,'condition_result':True}); self._execute_steps(s.get('body',[]))
        self.trace.add_step('WHILE',{'iteration':count,'condition_result':False})
    def _class(self,s):
        self.classes[s['name']]={'parent':s.get('parent'),'methods':{m['name']:m for m in s.get('methods',[])}}
        self.trace.add_step('CLASS',{'class_name':s['name'],'parent':s.get('parent'),'methods':list(self.classes[s['name']]['methods'])})
    def _inherit(self,s):
        child=s['child']; parent=s['parent']
        if child not in self.classes: self.classes[child]={'parent':parent,'methods':{}}
        else: self.classes[child]['parent']=parent
        self.trace.add_step('INHERIT',{'child':child,'parent':parent})
    def _object(self,s):
        cls=s['class'];
        if cls not in self.classes: raise ValueError(f"Class '{cls}' not defined")
        self.objects[s['name']]={'class':cls}; self.trace.variables[s['name']]=f"<object {cls}>"
        self.trace.add_step('OBJECT',{'object':s['name'],'class':cls})
    def _find_method(self,cls,name):
        seen=set()
        while cls and cls not in seen:
            seen.add(cls); data=self.classes.get(cls)
            if not data: return None,cls
            if name in data['methods']: return data['methods'][name],cls
            cls=data.get('parent')
        return None,cls
    def _call_method(self,s):
        obj=s['object'];
        if obj not in self.objects: raise ValueError(f"Object '{obj}' not defined")
        cls=self.objects[obj]['class']; method,owner=self._find_method(cls,s['method'])
        if not method: raise ValueError(f"Method '{s['method']}' not found for class '{cls}'")
        self.trace.add_step('CALL_METHOD',{'object':obj,'method':s['method'],'resolved_class':owner})
        self._execute_steps(method.get('body',[]))
    def _try_except(self,s):
        self.trace.add_step('TRY',{'status':'starting'})
        try: self._execute_steps(s.get('try_body',[]))
        except Exception as e:
            if s.get('exception_variable'): self.trace.variables[s['exception_variable']]=str(e)
            self.trace.add_step('EXCEPT',{'error':str(e),'exception_type':s.get('exception_type','Exception')})
            self._execute_steps(s.get('except_body',[]))
    def _raise(self,s):
        msg=str(self._value(s.get('message','An exception was raised'))); self.trace.add_step('RAISE',{'message':msg}); raise RuntimeError(msg)

if __name__=='__main__':
    print(ProgramInterpreter().execute_ir({'steps':[{'operation':'SET','variable':'x','value':10},{'operation':'ADD','variable':'x','value':5},{'operation':'PRINT','value':{'variable':'x'}}]}))
