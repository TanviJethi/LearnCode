"""
Local, offline parser: converts simple English instructions into the
interpreter's IR (Intermediate Representation) JSON structure.
No external API calls, no network required.

Supported patterns (case-insensitive), separated by '.' or newlines:
  - "Create x with 10" / "Set x to 10"        -> SET
  - "Add 5 to x"                                -> ADD
  - "Subtract 5 from x"                         -> SUBTRACT
  - "Multiply x by 2"                           -> MULTIPLY
  - "Divide x by 2"                             -> DIVIDE
  - "Print x" / "Print 'text'" / "Display x"    -> PRINT
  - "Repeat 5 times, add 1 to x"                -> REPEAT (single-line body)
  - "If x > 10, print 'Big'. Otherwise print 'Small'." -> IF/ELSE
"""

import re


class ParseError(Exception):
    pass


def _to_number(s):
    s = s.strip()
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        raise ParseError(f"Expected a number, got: '{s}'")


def _parse_print_target(rest):
    rest = rest.strip()
    quoted = re.match(r"""^['"](.+)['"]$""", rest)
    if quoted:
        return {"operation": "PRINT", "message": quoted.group(1)}
    return {"operation": "PRINT", "variable": rest}


def _parse_single_statement(text):
    text = text.strip()
    if not text:
        return None

    m = re.match(r"^(?:create|set)\s+(\w+)\s+(?:with|to)\s+(.+)$", text, re.I)
    if m:
        return {"operation": "SET", "variable": m.group(1), "value": _to_number(m.group(2))}

    m = re.match(r"^add\s+(.+?)\s+to\s+(\w+)$", text, re.I)
    if m:
        return {"operation": "ADD", "variable": m.group(2), "value": _to_number(m.group(1))}

    m = re.match(r"^subtract\s+(.+?)\s+from\s+(\w+)$", text, re.I)
    if m:
        return {"operation": "SUBTRACT", "variable": m.group(2), "value": _to_number(m.group(1))}

    m = re.match(r"^multiply\s+(\w+)\s+by\s+(.+)$", text, re.I)
    if m:
        return {"operation": "MULTIPLY", "variable": m.group(1), "value": _to_number(m.group(2))}

    m = re.match(r"^divide\s+(\w+)\s+by\s+(.+)$", text, re.I)
    if m:
        return {"operation": "DIVIDE", "variable": m.group(1), "value": _to_number(m.group(2))}

    m = re.match(r"^(?:print|display|show)\s+(.+)$", text, re.I)
    if m:
        return _parse_print_target(m.group(1))

    raise ParseError(f"Don't understand: '{text}'")


def parse_program(text):
    """
    Parse a multi-sentence natural language program into IR:
    {"steps": [...]}
    Raises ParseError with a friendly message on failure.
    """
    text = text.strip()
    if not text:
        raise ParseError("Please enter a program.")

    # Handle IF/OTHERWISE across the whole text first (they may span multiple '.'-separated clauses)
    if_match = re.search(
        r"if\s+(\w+)\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)?)\s*,?\s*(.+?)(?:\.\s*otherwise\s+(.+))?$",
        text,
        re.I | re.S,
    )
    if if_match:
        var, op, val, then_clause, else_clause = if_match.groups()
        steps_before = text[: if_match.start()]
        pre_steps = _parse_clauses(steps_before)

        then_stmt = _parse_single_statement(then_clause.rstrip(". "))
        else_stmt = _parse_single_statement(else_clause.rstrip(". ")) if else_clause else None

        if_step = {
            "operation": "IF",
            "condition": {"operator": op, "left": var, "right": _to_number(val)},
            "body": [then_stmt] if then_stmt else [],
            "else_body": [else_stmt] if else_stmt else [],
        }
        return {"steps": pre_steps + [if_step]}

    # Handle REPEAT N times, <body>
    repeat_match = re.search(r"repeat\s+(\d+)\s+times,?\s*(.+)$", text, re.I | re.S)
    if repeat_match:
        times_str, body_text = repeat_match.groups()
        steps_before = text[: repeat_match.start()]
        pre_steps = _parse_clauses(steps_before)
        body_steps = _parse_clauses(body_text)
        repeat_step = {
            "operation": "REPEAT",
            "times": int(times_str),
            "body": body_steps,
        }
        return {"steps": pre_steps + [repeat_step]}

    # Plain sequence of statements
    return {"steps": _parse_clauses(text)}


def _parse_clauses(text):
    clauses = [c.strip() for c in re.split(r"[.\n]", text) if c.strip()]
    steps = []
    for clause in clauses:
        stmt = _parse_single_statement(clause)
        if stmt:
            steps.append(stmt)
    return steps


def ir_to_python(ir_data):
    """Generate a rough Python code representation from IR, for the 'Generated Code' tab."""
    lines = []

    def render(steps, indent=0):
        pad = "    " * indent
        for step in steps:
            op = step.get("operation")
            if op == "SET":
                lines.append(f"{pad}{step['variable']} = {step['value']}")
            elif op == "ADD":
                lines.append(f"{pad}{step['variable']} = {step['variable']} + {step['value']}")
            elif op == "SUBTRACT":
                lines.append(f"{pad}{step['variable']} = {step['variable']} - {step['value']}")
            elif op == "MULTIPLY":
                lines.append(f"{pad}{step['variable']} = {step['variable']} * {step['value']}")
            elif op == "DIVIDE":
                lines.append(f"{pad}{step['variable']} = {step['variable']} // {step['value']}")
            elif op == "PRINT":
                if "variable" in step:
                    lines.append(f"{pad}print({step['variable']})")
                else:
                    lines.append(f'{pad}print("{step.get("message", "")}")')
            elif op == "IF":
                cond = step["condition"]
                lines.append(f"{pad}if {cond['left']} {cond['operator']} {cond['right']}:")
                render(step.get("body", []), indent + 1)
                if step.get("else_body"):
                    lines.append(f"{pad}else:")
                    render(step["else_body"], indent + 1)
            elif op == "REPEAT":
                lines.append(f"{pad}for i in range({step['times']}):")
                render(step.get("body", []), indent + 1)

    render(ir_data.get("steps", []))
    return "\n".join(lines) if lines else "# (nothing to show)"


def _infer_var_type(var_type_map, var_name):
    return var_type_map.get(var_name, "int")


def ir_to_cpp(ir_data):
    """Generate a rough C++ representation from IR, for the 'Generated Code' tab."""
    body_lines = []
    declared = set()

    def render(steps, indent=1):
        pad = "    " * indent
        for step in steps:
            op = step.get("operation")
            if op == "SET":
                var = step["variable"]
                val = step["value"]
                ctype = "double" if isinstance(val, float) else "int"
                if var not in declared:
                    body_lines.append(f"{pad}{ctype} {var} = {val};")
                    declared.add(var)
                else:
                    body_lines.append(f"{pad}{var} = {val};")
            elif op == "ADD":
                body_lines.append(f"{pad}{step['variable']} += {step['value']};")
            elif op == "SUBTRACT":
                body_lines.append(f"{pad}{step['variable']} -= {step['value']};")
            elif op == "MULTIPLY":
                body_lines.append(f"{pad}{step['variable']} *= {step['value']};")
            elif op == "DIVIDE":
                body_lines.append(f"{pad}{step['variable']} /= {step['value']};")
            elif op == "PRINT":
                if "variable" in step:
                    body_lines.append(f'{pad}std::cout << {step["variable"]} << std::endl;')
                else:
                    body_lines.append(f'{pad}std::cout << "{step.get("message", "")}" << std::endl;')
            elif op == "IF":
                cond = step["condition"]
                body_lines.append(f"{pad}if ({cond['left']} {cond['operator']} {cond['right']}) {{")
                render(step.get("body", []), indent + 1)
                if step.get("else_body"):
                    body_lines.append(f"{pad}}} else {{")
                    render(step["else_body"], indent + 1)
                body_lines.append(f"{pad}}}")
            elif op == "REPEAT":
                loop_var = "i"
                body_lines.append(f"{pad}for (int {loop_var} = 0; {loop_var} < {step['times']}; {loop_var}++) {{")
                render(step.get("body", []), indent + 1)
                body_lines.append(f"{pad}}}")

    render(ir_data.get("steps", []))
    header = ["#include <iostream>", "", "int main() {"]
    footer = ["    return 0;", "}"]
    if not body_lines:
        body_lines = ["    // (nothing to show)"]
    return "\n".join(header + body_lines + footer)


def ir_to_java(ir_data):
    """Generate a rough Java representation from IR, for the 'Generated Code' tab."""
    body_lines = []
    declared = set()

    def render(steps, indent=2):
        pad = "    " * indent
        for step in steps:
            op = step.get("operation")
            if op == "SET":
                var = step["variable"]
                val = step["value"]
                jtype = "double" if isinstance(val, float) else "int"
                if var not in declared:
                    body_lines.append(f"{pad}{jtype} {var} = {val};")
                    declared.add(var)
                else:
                    body_lines.append(f"{pad}{var} = {val};")
            elif op == "ADD":
                body_lines.append(f"{pad}{step['variable']} += {step['value']};")
            elif op == "SUBTRACT":
                body_lines.append(f"{pad}{step['variable']} -= {step['value']};")
            elif op == "MULTIPLY":
                body_lines.append(f"{pad}{step['variable']} *= {step['value']};")
            elif op == "DIVIDE":
                body_lines.append(f"{pad}{step['variable']} /= {step['value']};")
            elif op == "PRINT":
                if "variable" in step:
                    body_lines.append(f'{pad}System.out.println({step["variable"]});')
                else:
                    body_lines.append(f'{pad}System.out.println("{step.get("message", "")}");')
            elif op == "IF":
                cond = step["condition"]
                body_lines.append(f"{pad}if ({cond['left']} {cond['operator']} {cond['right']}) {{")
                render(step.get("body", []), indent + 1)
                if step.get("else_body"):
                    body_lines.append(f"{pad}}} else {{")
                    render(step["else_body"], indent + 1)
                body_lines.append(f"{pad}}}")
            elif op == "REPEAT":
                loop_var = "i"
                body_lines.append(f"{pad}for (int {loop_var} = 0; {loop_var} < {step['times']}; {loop_var}++) {{")
                render(step.get("body", []), indent + 1)
                body_lines.append(f"{pad}}}")

    render(ir_data.get("steps", []))
    header = ["public class Main {", "    public static void main(String[] args) {"]
    footer = ["    }", "}"]
    if not body_lines:
        body_lines = ["        // (nothing to show)"]
    return "\n".join(header + body_lines + footer)


# Syntax reference used by the app's "Syntax Guide" panel.
SYNTAX_GUIDE = [
    {
        "category": "Create / Set a variable",
        "patterns": ["Create <var> with <number>.", "Set <var> to <number>."],
        "example": "Create x with 10.",
    },
    {
        "category": "Add",
        "patterns": ["Add <number> to <var>."],
        "example": "Add 5 to x.",
    },
    {
        "category": "Subtract",
        "patterns": ["Subtract <number> from <var>."],
        "example": "Subtract 5 from x.",
    },
    {
        "category": "Multiply",
        "patterns": ["Multiply <var> by <number>."],
        "example": "Multiply x by 2.",
    },
    {
        "category": "Divide",
        "patterns": ["Divide <var> by <number>."],
        "example": "Divide x by 2.",
    },
    {
        "category": "Print",
        "patterns": ["Print <var>.", "Print 'text'.", "Display <var>.", "Show <var>."],
        "example": "Print x.  /  Print 'Hello'.",
    },
    {
        "category": "Repeat (loop)",
        "patterns": ["Repeat <N> times, <statement>."],
        "example": "Repeat 5 times, add 2 to y.",
    },
    {
        "category": "If / Otherwise (conditional)",
        "patterns": [
            "If <var> <op> <number>, <statement>. Otherwise <statement>.",
            "Operators: >  <  >=  <=  ==  !=",
        ],
        "example": "If n > 10, print 'Big'. Otherwise print 'Small'.",
    },
]
