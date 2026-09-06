import re

class ParseError(Exception):
    pass

LEVELS = {
    "LEVEL -1": ["Variables", "Numbers", "Strings", "Booleans", "Typecasting"],
    "LEVEL -2": ["Arithmetic operators", "Comparison operators", "Logical operators", "Assignment operators", "if / elif / else", "for loops", "while loops"],
    "LEVEL -3": ["Classes & objects", "Inheritance", "Polymorphism"],
    "LEVEL -4": ["try / except", "Raising exceptions"],
}
SUPPORTED_CONCEPTS = [c for concepts in LEVELS.values() for c in concepts]


def _clean_line(line):
    line = re.sub(r'^\s*(?:[-*]|\d+[.)])\s*', '', line)
    return line.strip()


def _split_sentences(text):
    # Keep quoted strings intact while splitting on periods/newlines.
    parts=[]; cur=[]; quote=None
    for ch in text:
        if ch in "'\"":
            if quote == ch: quote=None
            elif quote is None: quote=ch
        if (ch == '\n' or (ch == '.' and quote is None)) and quote is None:
            s=''.join(cur).strip()
            if s: parts.append(s)
            cur=[]
        else: cur.append(ch)
    s=''.join(cur).strip()
    if s: parts.append(s)
    return parts


def _literal(text, known=None, expression=False):
    text=text.strip().rstrip(',')
    if len(text)>=2 and text[0] in "'\"" and text[-1]==text[0]:
        return text[1:-1]
    low=text.lower()
    if low in ('true','false'): return low=='true'
    if low in ('none','null'): return None
    if re.fullmatch(r'-?\d+', text): return int(text)
    if re.fullmatch(r'-?(?:\d+\.\d*|\d*\.\d+)', text): return float(text)
    if known and text in known: return {"variable":text}
    if expression: return {"variable":text}
    return text


def _normalize_condition(s):
    s=s.strip().rstrip(':').strip()
    s=re.sub(r'\bis\s+greater\s+than\s+or\s+equal\s+to\b', ' >= ', s, flags=re.I)
    s=re.sub(r'\bis\s+less\s+than\s+or\s+equal\s+to\b', ' <= ', s, flags=re.I)
    s=re.sub(r'\bis\s+greater\s+than\b', ' > ', s, flags=re.I)
    s=re.sub(r'\bis\s+less\s+than\b', ' < ', s, flags=re.I)
    s=re.sub(r'\bis\s+not\s+equal\s+to\b', ' != ', s, flags=re.I)
    s=re.sub(r'\bis\s+equal\s+to\b', ' == ', s, flags=re.I)
    s=re.sub(r'\bequals\b', ' == ', s, flags=re.I)
    s=re.sub(r'\bis\b', ' == ', s, flags=re.I)
    s=re.sub(r'\s+', ' ', s).strip()
    return s


def _expr(text, known=None, condition=False):
    text=text.strip().rstrip(':').strip()
    if condition:
        text=_normalize_condition(text)
    # Simple natural-language comparison with no symbolic operator parser needed.
    tokens=re.findall(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|>=|<=|==|!=|>|<|\+|-|\*|/|%|\(|\)|\b(?:and|or|not)\b|[^\s+*/%()<>!=]+', text, flags=re.I)
    if not tokens:
        raise ParseError("Missing expression")

    pos=0
    def atom():
        nonlocal pos
        if pos>=len(tokens): raise ParseError("Incomplete expression")
        t=tokens[pos]; pos+=1
        if t=='(':
            v=logical()
            if pos>=len(tokens) or tokens[pos]!=')': raise ParseError("Missing ')'")
            pos+=1; return v
        if t.lower()=='not': return {"type":"logical","operator":"not","value":atom()}
        return _literal(t, known, expression=True)
    def mul():
        nonlocal pos
        left=atom()
        while pos<len(tokens) and tokens[pos] in ('*','/','%'):
            op=tokens[pos]; pos+=1; right=atom()
            left={"type":"arithmetic","operator":op,"left":left,"right":right}
        return left
    def add():
        nonlocal pos
        left=mul()
        while pos<len(tokens) and tokens[pos] in ('+','-'):
            op=tokens[pos]; pos+=1; right=mul()
            left={"type":"arithmetic","operator":op,"left":left,"right":right}
        return left
    def compare():
        nonlocal pos
        left=add()
        if pos<len(tokens) and tokens[pos] in ('>','<','>=','<=','==','!='):
            op=tokens[pos]; pos+=1; right=add()
            return {"type":"comparison","operator":op,"left":left,"right":right}
        return left
    def logical_and():
        nonlocal pos
        left=compare()
        while pos<len(tokens) and tokens[pos].lower()=='and':
            pos+=1; right=compare(); left={"type":"logical","operator":"and","left":left,"right":right}
        return left
    def logical():
        nonlocal pos
        left=logical_and()
        while pos<len(tokens) and tokens[pos].lower()=='or':
            pos+=1; right=logical_and(); left={"type":"logical","operator":"or","left":left,"right":right}
        return left
    result=logical()
    if pos != len(tokens):
        raise ParseError(f"Could not understand expression: '{text}'")
    return result


def _value(text, known):
    text=text.strip()
    if re.search(r'(?:>=|<=|==|!=|>|<|\+|\*|/|%|\band\b|\bor\b)', text, re.I):
        return _expr(text, known)
    if re.fullmatch(r'[A-Za-z_]\w*', text) and text in known:
        return {"variable":text}
    return _literal(text, known)


def _statement(text, known):
    text=_clean_line(text).rstrip(';').strip()
    if not text: return None
    # type-specific variable creation
    m=re.match(r'^(?:create|make)\s+(?:a\s+)?(number|numeric|integer|float|decimal|string|text|boolean|bool)\s+(?:variable\s+)?([A-Za-z_]\w*)\s+(?:with|as|equal to)\s+(.+)$',text,re.I)
    if m:
        typ,name,val=m.groups(); v=_value(val,known); known.add(name)
        return {"operation":"SET","variable":name,"value":v,"declared_type":typ.lower()}
    m=re.match(r'^(?:create|set|make)\s+(?:variable\s+)?([A-Za-z_]\w*)\s+(?:with|to|as|equal to)\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups(); v=_value(val,known); known.add(name)
        return {"operation":"SET","variable":name,"value":v}
    m=re.match(r'^convert\s+([A-Za-z_]\w*)\s+to\s+(integer|int|float|decimal|string|str|boolean|bool)$',text,re.I)
    if m:
        name,typ=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"TYPECAST","variable":name,"target_type":typ.lower()}
    m=re.match(r'^(?:typecast|cast)\s+([A-Za-z_]\w*)\s+as\s+(integer|int|float|decimal|string|str|boolean|bool)$',text,re.I)
    if m:
        name,typ=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"TYPECAST","variable":name,"target_type":typ.lower()}
    m=re.match(r'^add\s+(.+?)\s+to\s+([A-Za-z_]\w*)$',text,re.I)
    if m:
        val,name=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"ADD","variable":name,"value":_value(val,known)}
    m=re.match(r'^subtract\s+(.+?)\s+from\s+([A-Za-z_]\w*)$',text,re.I)
    if m:
        val,name=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"SUBTRACT","variable":name,"value":_value(val,known)}
    m=re.match(r'^multiply\s+([A-Za-z_]\w*)\s+by\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"MULTIPLY","variable":name,"value":_value(val,known)}
    m=re.match(r'^divide\s+([A-Za-z_]\w*)\s+by\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"DIVIDE","variable":name,"value":_value(val,known)}
    m=re.match(r'^mod(?:ulo)?\s+([A-Za-z_]\w*)\s+by\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups();
        if name not in known: raise ParseError(f"Variable '{name}' is not defined")
        return {"operation":"MODULO","variable":name,"value":_value(val,known)}
    m=re.match(r'^(?:increase|increment)\s+([A-Za-z_]\w*)\s+by\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups(); return {"operation":"ADD","variable":name,"value":_value(val,known)}
    m=re.match(r'^(?:decrease|decrement)\s+([A-Za-z_]\w*)\s+by\s+(.+)$',text,re.I)
    if m:
        name,val=m.groups(); return {"operation":"SUBTRACT","variable":name,"value":_value(val,known)}
    m=re.match(r'^(?:print|display|show)\s+(.+)$',text,re.I)
    if m:
        target=m.group(1).strip();
        if len(target)>=2 and target[0] in "'\"" and target[-1]==target[0]: return {"operation":"PRINT","value":target[1:-1]}
        if target in known: return {"operation":"PRINT","value":{"variable":target}}
        return {"operation":"PRINT","value":_literal(target,known)}
    m=re.match(r'^raise\s+(?:an?\s+)?(?:exception|error)?\s*(?:with\s+)?(?:message\s+)?[:,-]?\s*(.*)$',text,re.I)
    if m and (text.lower().startswith('raise')):
        msg=m.group(1).strip() or 'An exception was raised'
        return {"operation":"RAISE","message":_value(msg,known)}
    m=re.match(r'^(?:create|make)\s+(?:an?\s+)?object\s+([A-Za-z_]\w*)\s+(?:of|from)\s+([A-Za-z_]\w*)$',text,re.I)
    if m:
        obj,cls=m.groups(); return {"operation":"OBJECT","name":obj,"class":cls}
    m=re.match(r'^(?:call|invoke)\s+(?:method\s+)?([A-Za-z_]\w*)\s+(?:on|of)\s+([A-Za-z_]\w*)$',text,re.I)
    if m:
        method,obj=m.groups(); return {"operation":"CALL_METHOD","object":obj,"method":method}
    m=re.match(r'^([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(\s*\)$',text)
    if m: return {"operation":"CALL_METHOD","object":m.group(1),"method":m.group(2)}
    raise ParseError(f"Don't understand: '{text}'")


def _indent_lines(text):
    raw=[]
    for n,line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        expanded=line.replace('\t','    ')
        indent=len(expanded)-len(expanded.lstrip(' '))
        raw.append((indent,_clean_line(expanded),n))
    return raw


def _parse_block(items, index=0, base_indent=None, known=None, stop_keywords=()):
    if known is None: known=set()
    if base_indent is None: base_indent=items[index][0] if index<len(items) else 0
    steps=[]
    while index<len(items):
        indent,line,ln=items[index]
        if indent < base_indent: break
        if indent > base_indent: raise ParseError(f"Unexpected indentation on line {ln}")
        low=line.lower()
        if any(low.startswith(k) for k in stop_keywords): break
        # IF chain
        if re.match(r'^if\s+',line,re.I):
            condition=line[2:].strip()
            inline=None
            if ':' in condition:
                condition,inline=condition.split(':',1); inline=inline.strip()
            elif re.search(r'\bthen\b',condition,re.I):
                condition,inline=re.split(r'\bthen\b',condition,maxsplit=1,flags=re.I); inline=inline.strip()
            condition=condition.rstrip(',').strip()
            body=[]
            index+=1
            if inline: body=[_statement(inline,known)]
            elif index<len(items) and items[index][0]>base_indent:
                body,index=_parse_block(items,index,items[index][0],known,('elif ','else','otherwise'))
            elif index<len(items) and items[index][0]<=base_indent: body=[]
            elif not inline: raise ParseError(f"IF on line {ln} needs an indented body or inline action")
            elif index<len(items): pass
            elif not body: raise ParseError(f"IF on line {ln} has no action")
            elif inline: pass
            # consume elif/else at same indent
            elifs=[]; else_body=[]
            while index<len(items) and items[index][0]==base_indent and re.match(r'^elif\s+',items[index][1],re.I):
                _,el,eln=items[index]; c=el[4:].strip(); inl=None
                if ':' in c: c,inl=c.split(':',1); inl=inl.strip()
                elif re.search(r'\bthen\b',c,re.I): c,inl=re.split(r'\bthen\b',c,maxsplit=1,flags=re.I); inl=inl.strip()
                index+=1; b=[]
                if inl: b=[_statement(inl,known)]
                elif index<len(items) and items[index][0]>base_indent: b,index=_parse_block(items,index,items[index][0],known,('elif ','else','otherwise'))
                elif not inl: raise ParseError(f"ELIF on line {eln} needs a body")
                elifs.append({"condition":_expr(c,known,True),"body":b})
            if index<len(items) and items[index][0]==base_indent and re.match(r'^(?:else|otherwise)\b',items[index][1],re.I):
                _,el,eln=items[index]; rest=re.sub(r'^(?:else|otherwise)\b','',el,flags=re.I).strip(); index+=1
                if rest.startswith(':'): rest=rest[1:].strip()
                if rest: else_body=[_statement(rest,known)]
                elif index<len(items) and items[index][0]>base_indent: else_body,index=_parse_block(items,index,items[index][0],known,('elif ','else','otherwise'))
                else: raise ParseError(f"ELSE on line {eln} needs a body")
            steps.append({"operation":"IF","condition":_expr(condition,known,True),"body":body,"elif":elifs,"else_body":else_body}); continue
        # FOR
        m=re.match(r'^for\s+([A-Za-z_]\w*)\s+from\s+(.+?)\s+to\s+(.+?)(?::|$)',line,re.I)
        if m:
            var,a,b=m.groups(); index+=1; body=[]
            if index<len(items) and items[index][0]>base_indent: body,index=_parse_block(items,index,items[index][0],known)
            elif line.rstrip().endswith(':') and index>=len(items): raise ParseError(f"FOR on line {ln} needs a body")
            known.add(var); steps.append({"operation":"FOR","variable":var,"start":_value(a,known),"end":_value(b,known),"body":body}); continue
        m=re.match(r'^repeat\s+(.+?)\s+times(?:,|:)?\s*(.*)$',line,re.I)
        if m:
            times,inline=m.groups(); index+=1; body=[]
            if inline.strip(): body=[_statement(inline,known)]
            elif index<len(items) and items[index][0]>base_indent: body,index=_parse_block(items,index,items[index][0],known)
            else: raise ParseError(f"REPEAT on line {ln} needs a body")
            steps.append({"operation":"REPEAT","times":_value(times,known),"body":body}); continue
        # WHILE
        m=re.match(r'^while\s+(.+?)(?::|$)',line,re.I)
        if m:
            cond=m.group(1); index+=1; body=[]
            if index<len(items) and items[index][0]>base_indent: body,index=_parse_block(items,index,items[index][0],known)
            else: raise ParseError(f"WHILE on line {ln} needs a body")
            steps.append({"operation":"WHILE","condition":_expr(cond,known,True),"body":body}); continue
        # TRY / EXCEPT
        if re.match(r'^try\s*:?(?:\s+.*)?$',line,re.I):
            rest=re.sub(r'^try\s*:?','',line,flags=re.I).strip(); index+=1
            try_body=[]
            if rest: try_body=[_statement(rest,known)]
            elif index<len(items) and items[index][0]>base_indent: try_body,index=_parse_block(items,index,items[index][0],known,('except',))
            else: raise ParseError(f"TRY on line {ln} needs a body")
            if index>=len(items) or items[index][0]!=base_indent or not re.match(r'^except\b',items[index][1],re.I):
                raise ParseError(f"TRY on line {ln} must be followed by EXCEPT")
            _,eline,eln=items[index]; erest=re.sub(r'^except\b','',eline,flags=re.I).strip(); index+=1
            exception_type='Exception'
            mt=re.match(r'^(?:an?\s+)?([A-Za-z_]\w*)?(?:\s*[:,-].*)?$',erest)
            if erest and mt and mt.group(1): exception_type=mt.group(1)
            except_body=[]
            if index<len(items) and items[index][0]>base_indent: except_body,index=_parse_block(items,index,items[index][0],known)
            else: raise ParseError(f"EXCEPT on line {eln} needs a body")
            steps.append({"operation":"TRY_EXCEPT","exception_type":exception_type,"try_body":try_body,"except_body":except_body}); continue
        # class
        m=re.match(r'^(?:create|make)\s+(?:a\s+)?class\s+([A-Za-z_]\w*)(?:\s+(?:that\s+)?inherits?\s+([A-Za-z_]\w*))?\s*:?$',line,re.I)
        if m:
            name,parent=m.groups(); index+=1; methods=[]
            while index<len(items) and items[index][0]>base_indent:
                mind,mline,mln=items[index]
                mm=re.match(r'^(?:create\s+)?(?:a\s+)?method\s+([A-Za-z_]\w*)|^[A-Za-z_]\w*\s+has\s+(?:a\s+)?method\s+([A-Za-z_]\w*)',mline,re.I)
                if not mm: raise ParseError(f"Inside class '{name}', expected a method on line {mln}")
                method=mm.group(1) or mm.group(2); index+=1; body=[]
                if index<len(items) and items[index][0]>mind: body,index=_parse_block(items,index,items[index][0],known)
                else: raise ParseError(f"Method '{method}' needs a body")
                methods.append({"name":method,"body":body})
            steps.append({"operation":"CLASS","name":name,"parent":parent,"methods":methods}); continue
        m=re.match(r'^([A-Za-z_]\w*)\s+inherits\s+([A-Za-z_]\w*)\s*:??$',line,re.I)
        if m: steps.append({"operation":"INHERIT","child":m.group(1),"parent":m.group(2)}); index+=1; continue
        try:
            st=_statement(line,known); 
        except ParseError as e:
            raise ParseError(f"Line {ln}: {e}")
        if st: steps.append(st)
        index+=1
    return steps,index


def parse_program(text):
    if not text or not text.strip(): raise ParseError("Please enter a program.")
    items=_indent_lines(text)
    # For single-line natural English with periods, convert to pseudo-lines.
    if len(items)==1 and '.' in items[0][1]:
        items=[]
        for i,s in enumerate(_split_sentences(text),1): items.append((0,s,i))
    steps,_=_parse_block(items,0,items[0][0],set())
    return {"steps":steps}


def _val_py(v):
    if isinstance(v,dict):
        t=v.get('type')
        if 'variable' in v and len(v)==1: return v['variable']
        if t=='arithmetic': return f"({_val_py(v['left'])} {v['operator']} {_val_py(v['right'])})"
        if t=='comparison': return f"({_val_py(v['left'])} {v['operator']} {_val_py(v['right'])})"
        if t=='logical':
            if v['operator']=='not': return f"(not {_val_py(v['value'])})"
            return f"({_val_py(v['left'])} {v['operator']} { _val_py(v['right'])})"
    if isinstance(v,str): return repr(v)
    if v is None: return 'None'
    if isinstance(v,bool): return 'True' if v else 'False'
    return str(v)


def _render_py(steps,indent=0):
    out=[]; p='    '*indent
    for s in steps:
        op=s['operation']
        if op=='SET': out.append(f"{p}{s['variable']} = {_val_py(s['value'])}")
        elif op in ('ADD','SUBTRACT','MULTIPLY','DIVIDE','MODULO'):
            sym={'ADD':'+=','SUBTRACT':'-=','MULTIPLY':'*=','DIVIDE':'/=','MODULO':'%='}[op]; out.append(f"{p}{s['variable']} {sym} {_val_py(s['value'])}")
        elif op=='TYPECAST':
            typ={'int':'int','integer':'int','float':'float','decimal':'float','str':'str','string':'str','bool':'bool','boolean':'bool'}[s['target_type']]; out.append(f"{p}{s['variable']} = {typ}({s['variable']})")
        elif op=='PRINT': out.append(f"{p}print({_val_py(s['value'])})")
        elif op=='IF':
            out.append(f"{p}if {_val_py(s['condition'])}:"); out += _render_py(s['body'],indent+1) or [p+'    pass']
            for e in s.get('elif',[]): out.append(f"{p}elif {_val_py(e['condition'])}:"); out += _render_py(e['body'],indent+1) or [p+'    pass']
            if s.get('else_body'): out.append(f"{p}else:"); out += _render_py(s['else_body'],indent+1)
        elif op=='REPEAT': out.append(f"{p}for _ in range({_val_py(s['times'])}):"); out += _render_py(s['body'],indent+1) or [p+'    pass']
        elif op=='FOR': out.append(f"{p}for {s['variable']} in range({_val_py(s['start'])}, {_val_py(s['end'])} + 1):"); out += _render_py(s['body'],indent+1) or [p+'    pass']
        elif op=='WHILE': out.append(f"{p}while {_val_py(s['condition'])}:"); out += _render_py(s['body'],indent+1) or [p+'    pass']
        elif op=='RAISE': out.append(f"{p}raise Exception({_val_py(s['message'])})")
        elif op=='TRY_EXCEPT':
            out.append(f"{p}try:"); out += _render_py(s['try_body'],indent+1) or [p+'    pass']; out.append(f"{p}except Exception as e:"); out += _render_py(s['except_body'],indent+1) or [p+'    pass']
        elif op=='CLASS':
            parent=f"({s['parent']})" if s.get('parent') else '' ; out.append(f"{p}class {s['name']}{parent}:")
            if not s.get('methods'): out.append(p+'    pass')
            for m in s.get('methods',[]): out.append(f"{p}    def {m['name']}(self):"); out += _render_py(m['body'],indent+2) or [p+'        pass']
        elif op=='INHERIT': out.append(f"{p}# {s['child']} inherits {s['parent']}")
        elif op=='OBJECT': out.append(f"{p}{s['name']} = {s['class']}()")
        elif op=='CALL_METHOD': out.append(f"{p}{s['object']}.{s['method']}()")
    return out


def ir_to_python(ir_data): return '\n'.join(_render_py(ir_data.get('steps',[]))) or '# (nothing to show)'


def _cpp_val(v):
    if isinstance(v,dict):
        t=v.get('type')
        if 'variable' in v and len(v)==1:return v['variable']
        if t in ('arithmetic','comparison'): return f"({_cpp_val(v['left'])} {v['operator']} {_cpp_val(v['right'])})"
        if t=='logical':
            if v['operator']=='not': return f"(!{_cpp_val(v['value'])})"
            op='&&' if v['operator']=='and' else '||'; return f"({_cpp_val(v['left'])} {op} {_cpp_val(v['right'])})"
    if isinstance(v,str): return '"'+v.replace('"','\\"')+'"'
    if v is None:return 'nullptr'
    if isinstance(v,bool):return 'true' if v else 'false'
    return str(v)


def _infer_cpp(v,declared_type=None):
    if declared_type: return {'number':'int','numeric':'double','integer':'int','float':'double','decimal':'double','string':'string','text':'string','boolean':'bool','bool':'bool'}.get(declared_type,'auto')
    if isinstance(v,bool):return 'bool'
    if isinstance(v,int):return 'int'
    if isinstance(v,float):return 'double'
    if isinstance(v,str):return 'string'
    return 'auto'


def _render_cpp(steps,indent=1,declared=None):
    if declared is None: declared=set()
    out=[]; p='    '*indent
    for s in steps:
        op=s['operation']
        if op=='SET':
            v=s['variable']; x=_cpp_val(s['value']);
            if v not in declared: out.append(f"{p}{_infer_cpp(s['value'],s.get('declared_type'))} {v} = {x};"); declared.add(v)
            else: out.append(f"{p}{v} = {x};")
        elif op in ('ADD','SUBTRACT','MULTIPLY','DIVIDE','MODULO'):
            sym={'ADD':'+=','SUBTRACT':'-=','MULTIPLY':'*=','DIVIDE':'/=','MODULO':'%='}[op]; out.append(f"{p}{s['variable']} {sym} {_cpp_val(s['value'])};")
        elif op=='TYPECAST': out.append(f"{p}{s['variable']} = static_cast<{ {'int':'int','integer':'int','float':'double','decimal':'double','string':'string','str':'string','bool':'bool','boolean':'bool'}[s['target_type']] }>({s['variable']});")
        elif op=='PRINT': out.append(f"{p}cout << {_cpp_val(s['value'])} << endl;")
        elif op=='IF':
            out.append(f"{p}if ({_cpp_val(s['condition'])}) {{"); out+=_render_cpp(s['body'],indent+1,declared); 
            for e in s.get('elif',[]): out.append(f"{p}}} else if ({_cpp_val(e['condition'])}) {{"); out+=_render_cpp(e['body'],indent+1,declared)
            if s.get('else_body'): out.append(f"{p}}} else {{"); out+=_render_cpp(s['else_body'],indent+1,declared)
            out.append(f"{p}}}")
        elif op=='REPEAT': out.append(f"{p}for (int _i = 0; _i < {_cpp_val(s['times'])}; ++_i) {{"); out+=_render_cpp(s['body'],indent+1,declared); out.append(f"{p}}}")
        elif op=='FOR': out.append(f"{p}for (int {s['variable']} = {_cpp_val(s['start'])}; {s['variable']} <= {_cpp_val(s['end'])}; ++{s['variable']}) {{"); out+=_render_cpp(s['body'],indent+1,declared); out.append(f"{p}}}")
        elif op=='WHILE': out.append(f"{p}while ({_cpp_val(s['condition'])}) {{"); out+=_render_cpp(s['body'],indent+1,declared); out.append(f"{p}}}")
        elif op=='RAISE': out.append(f"{p}throw runtime_error({_cpp_val(s['message'])});")
        elif op=='TRY_EXCEPT': out.append(f"{p}try {{"); out+=_render_cpp(s['try_body'],indent+1,declared); out.append(f"{p}}} catch (const exception& e) {{"); out+=_render_cpp(s['except_body'],indent+1,declared); out.append(f"{p}}}")
        elif op=='CLASS':
            parent=f" : public {s['parent']}" if s.get('parent') else ''; out.append(f"{p}class {s['name']}{parent} {{"); out.append(f"{p}public:")
            for m in s.get('methods',[]): out.append(f"{p}    void {m['name']}() {{"); out+=_render_cpp(m['body'],indent+2,set()); out.append(f"{p}    }}")
            out.append(f"{p}}};")
        elif op=='OBJECT': out.append(f"{p}{s['class']} {s['name']};")
        elif op=='CALL_METHOD': out.append(f"{p}{s['object']}.{s['method']}();")
    return out


def ir_to_cpp(ir_data):
    steps=ir_data.get('steps',[])
    class_steps=[x for x in steps if x.get('operation')=='CLASS']
    main_steps=[x for x in steps if x.get('operation')!='CLASS']
    class_lines=_render_cpp(class_steps,0,set())
    body=_render_cpp(main_steps,1,set())
    return '\n'.join(['#include <iostream>','#include <string>','#include <stdexcept>','#include <exception>','using namespace std;',''] + class_lines + ([''] if class_lines else []) + ['int main() {'] + (body or ['    // (nothing to show)']) + ['    return 0;','}'])


def _java_val(v):
    if isinstance(v,dict):
        t=v.get('type')
        if 'variable' in v and len(v)==1:return v['variable']
        if t in ('arithmetic','comparison'): return f"({_java_val(v['left'])} {v['operator']} {_java_val(v['right'])})"
        if t=='logical':
            if v['operator']=='not':return f"(!{_java_val(v['value'])})"
            op='&&' if v['operator']=='and' else '||';return f"({_java_val(v['left'])} {op} {_java_val(v['right'])})"
    if isinstance(v,str):return '"'+v.replace('"','\\"')+'"'
    if v is None:return 'null'
    if isinstance(v,bool):return 'true' if v else 'false'
    return str(v)


def _infer_java(v,declared_type=None):
    if declared_type:return {'number':'int','numeric':'double','integer':'int','float':'double','decimal':'double','string':'String','text':'String','boolean':'boolean','bool':'boolean'}.get(declared_type,'var')
    if isinstance(v,bool):return 'boolean'
    if isinstance(v,int):return 'int'
    if isinstance(v,float):return 'double'
    if isinstance(v,str):return 'String'
    return 'var'


def _render_java(steps,indent=2,declared=None):
    if declared is None:declared=set()
    out=[];p='    '*indent
    for s in steps:
        op=s['operation']
        if op=='SET':
            v=s['variable']; x=_java_val(s['value']);
            if v not in declared: out.append(f"{p}{_infer_java(s['value'],s.get('declared_type'))} {v} = {x};");declared.add(v)
            else:out.append(f"{p}{v} = {x};")
        elif op in ('ADD','SUBTRACT','MULTIPLY','DIVIDE','MODULO'):
            sym={'ADD':'+=','SUBTRACT':'-=','MULTIPLY':'*=','DIVIDE':'/=','MODULO':'%='}[op];out.append(f"{p}{s['variable']} {sym} {_java_val(s['value'])};")
        elif op=='TYPECAST':
            typ=s['target_type']; cast={'int':'int','integer':'int','float':'double','decimal':'double','string':'String','str':'String','bool':'boolean','boolean':'boolean'}[typ]
            if cast=='String':out.append(f'{p}{s["variable"]} = String.valueOf({s["variable"]});')
            else:out.append(f"{p}{s['variable']} = ({cast}) {s['variable']};")
        elif op=='PRINT':out.append(f"{p}System.out.println({_java_val(s['value'])});")
        elif op=='IF':
            out.append(f"{p}if ({_java_val(s['condition'])}) {{");out+=_render_java(s['body'],indent+1,declared)
            for e in s.get('elif',[]):out.append(f"{p}}} else if ({_java_val(e['condition'])}) {{");out+=_render_java(e['body'],indent+1,declared)
            if s.get('else_body'):out.append(f"{p}}} else {{");out+=_render_java(s['else_body'],indent+1,declared)
            out.append(f"{p}}}")
        elif op=='REPEAT':out.append(f"{p}for (int _i = 0; _i < {_java_val(s['times'])}; _i++) {{");out+=_render_java(s['body'],indent+1,declared);out.append(f"{p}}}")
        elif op=='FOR':out.append(f"{p}for (int {s['variable']} = {_java_val(s['start'])}; {s['variable']} <= {_java_val(s['end'])}; {s['variable']}++) {{");out+=_render_java(s['body'],indent+1,declared);out.append(f"{p}}}")
        elif op=='WHILE':out.append(f"{p}while ({_java_val(s['condition'])}) {{");out+=_render_java(s['body'],indent+1,declared);out.append(f"{p}}}")
        elif op=='RAISE':out.append(f"{p}throw new RuntimeException({_java_val(s['message'])});")
        elif op=='TRY_EXCEPT':out.append(f"{p}try {{");out+=_render_java(s['try_body'],indent+1,declared);out.append(f"{p}}} catch (Exception e) {{");out+=_render_java(s['except_body'],indent+1,declared);out.append(f"{p}}}")
        elif op=='CLASS':
            parent=f" extends {s['parent']}" if s.get('parent') else '';out.append(f"{p}static class {s['name']}{parent} {{")
            for m in s.get('methods',[]):out.append(f"{p}    void {m['name']}() {{");out+=_render_java(m['body'],indent+2,set());out.append(f"{p}    }}")
            out.append(f"{p}}}")
        elif op=='OBJECT':out.append(f"{p}{s['class']} {s['name']} = new {s['class']}();")
        elif op=='CALL_METHOD':out.append(f"{p}{s['object']}.{s['method']}();")
    return out


def ir_to_java(ir_data):
    steps=ir_data.get('steps',[])
    class_steps=[x for x in steps if x.get('operation')=='CLASS']
    main_steps=[x for x in steps if x.get('operation')!='CLASS']
    classes=_render_java(class_steps,1,set())
    body=_render_java(main_steps,2,set())
    return '\n'.join(['public class Main {'] + classes + ([''] if classes else []) + ['    public static void main(String[] args) {'] + (body or ['        // (nothing to show)']) + ['    }','}'])

SYNTAX_GUIDE=[]
for level,concepts in LEVELS.items():
    for concept in concepts:
        examples={
            'Variables':'Create age with 10.', 'Numbers':'Create a number score with 95.', 'Strings':'Create a string name with "Tanvi".', 'Booleans':'Create a boolean happy with true.', 'Typecasting':'Convert age to string.',
            'Arithmetic operators':'Set total to 10 + 5 * 2.', 'Comparison operators':'If age is greater than 10: Print "Older".', 'Logical operators':'If age > 10 and happy == true: Print "Yes".', 'Assignment operators':'Add 5 to score.',
            'if / elif / else':'If score >= 90: Print "A"\nElif score >= 60: Print "B"\nElse: Print "C".', 'for loops':'For i from 1 to 5: Print i.', 'while loops':'While x < 5: Add 1 to x.',
            'Classes & objects':'Create a class Animal:\n    Create a method speak:\n        Print "Hello".\nCreate an object dog of Animal.\nCall speak on dog.', 'Inheritance':'Create a class Dog that inherits Animal:', 'Polymorphism':'Create a class Dog that inherits Animal and defines the same speak method.',
            'try / except':'Try:\n    Raise exception with "Something went wrong".\nExcept:\n    Print "Handled".', 'Raising exceptions':'Raise exception with "Invalid value".'}
        SYNTAX_GUIDE.append({'category':f'{level} — {concept}','patterns':[examples.get(concept,'')],'example':examples.get(concept,'')})
