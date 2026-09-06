"""
Custom Python Interpreter for Educational Programming Platform
Executes a controlled set of operations from Intermediate Representation (IR)
Generates step-by-step execution traces for visualization
"""

import json
from typing import Any, Dict, List, Optional, Union


class ExecutionTrace:
    """Records every step of program execution"""
    
    def __init__(self):
        self.steps = []
        self.variables = {}
        self.output = []
        self.step_count = 0
    
    def add_step(self, operation: str, details: Dict[str, Any]):
        """Record a single step"""
        self.step_count += 1
        step = {
            "step": self.step_count,
            "operation": operation,
            "timestamp": len(self.steps),
            "variables_before": dict(self.variables),
            **details
        }
        self.steps.append(step)
    
    def to_dict(self):
        """Convert trace to JSON-serializable format"""
        return {
            "total_steps": self.step_count,
            "steps": self.steps,
            "final_variables": self.variables,
            "output": self.output
        }


class ProgramInterpreter:
    """
    Executes IR instructions with a controlled symbol table and execution engine.
    Prevents arbitrary code execution.
    """
    
    ALLOWED_OPERATIONS = {
        "SET", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "MODULO",
        "PRINT", "IF", "ELSE", "END", "REPEAT", "WHILE"
    }
    
    MAX_ITERATIONS = 1000
    
    def __init__(self):
        self.trace = ExecutionTrace()
        self.call_stack = []
        self.iteration_count = 0
    
    def execute_ir(self, ir_json: Union[str, Dict]) -> Dict[str, Any]:
        """
        Main entry point: Execute IR and return execution trace
        
        Args:
            ir_json: Either a JSON string or dict with 'steps' key
        
        Returns:
            Execution trace dict
        """
        try:
            # Parse IR
            if isinstance(ir_json, str):
                ir_data = json.loads(ir_json)
            else:
                ir_data = ir_json
            
            if "steps" not in ir_data:
                raise ValueError("IR must contain 'steps' key")
            
            # Execute steps
            self._execute_steps(ir_data["steps"])
            
        except Exception as e:
            self.trace.steps.append({
                "step": self.trace.step_count + 1,
                "operation": "ERROR",
                "error": str(e)
            })
        
        return self.trace.to_dict()
    
    def _execute_steps(self, steps: List[Dict[str, Any]]):
        """Execute a list of IR steps"""
        i = 0
        while i < len(steps):
            step = steps[i]
            operation = step.get("operation", "").upper()
            
            if operation == "SET":
                self._execute_set(step)
            elif operation == "ADD":
                self._execute_add(step)
            elif operation == "SUBTRACT":
                self._execute_subtract(step)
            elif operation == "MULTIPLY":
                self._execute_multiply(step)
            elif operation == "DIVIDE":
                self._execute_divide(step)
            elif operation == "MODULO":
                self._execute_modulo(step)
            elif operation == "PRINT":
                self._execute_print(step)
            elif operation == "IF":
                # Skip to matching END or ELSE
                i = self._execute_if(step, steps, i)
                continue
            elif operation == "REPEAT":
                # Handle loop
                i = self._execute_repeat(step, steps, i)
                continue
            else:
                self.trace.add_step("ERROR", {"error": f"Unknown operation: {operation}"})
            
            i += 1
    
    def _execute_set(self, step: Dict):
        """SET variable value"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if not var_name:
            raise ValueError("SET requires 'variable' key")
        
        self.trace.variables[var_name] = value
        self.trace.add_step("SET", {
            "variable": var_name,
            "value": value,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_add(self, step: Dict):
        """ADD value to variable"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if var_name not in self.trace.variables:
            raise ValueError(f"Variable '{var_name}' not defined")
        
        old_val = self.trace.variables[var_name]
        new_val = old_val + value
        self.trace.variables[var_name] = new_val
        
        self.trace.add_step("ADD", {
            "variable": var_name,
            "operand": value,
            "old_value": old_val,
            "new_value": new_val,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_subtract(self, step: Dict):
        """SUBTRACT value from variable"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if var_name not in self.trace.variables:
            raise ValueError(f"Variable '{var_name}' not defined")
        
        old_val = self.trace.variables[var_name]
        new_val = old_val - value
        self.trace.variables[var_name] = new_val
        
        self.trace.add_step("SUBTRACT", {
            "variable": var_name,
            "operand": value,
            "old_value": old_val,
            "new_value": new_val,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_multiply(self, step: Dict):
        """MULTIPLY variable by value"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if var_name not in self.trace.variables:
            raise ValueError(f"Variable '{var_name}' not defined")
        
        old_val = self.trace.variables[var_name]
        new_val = old_val * value
        self.trace.variables[var_name] = new_val
        
        self.trace.add_step("MULTIPLY", {
            "variable": var_name,
            "operand": value,
            "old_value": old_val,
            "new_value": new_val,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_divide(self, step: Dict):
        """DIVIDE variable by value"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if var_name not in self.trace.variables:
            raise ValueError(f"Variable '{var_name}' not defined")
        
        if value == 0:
            raise ValueError("Division by zero")
        
        old_val = self.trace.variables[var_name]
        new_val = old_val // value  # Integer division for clarity
        self.trace.variables[var_name] = new_val
        
        self.trace.add_step("DIVIDE", {
            "variable": var_name,
            "operand": value,
            "old_value": old_val,
            "new_value": new_val,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_modulo(self, step: Dict):
        """MODULO operation"""
        var_name = step.get("variable")
        value = step.get("value")
        
        if var_name not in self.trace.variables:
            raise ValueError(f"Variable '{var_name}' not defined")
        
        old_val = self.trace.variables[var_name]
        new_val = old_val % value
        self.trace.variables[var_name] = new_val
        
        self.trace.add_step("MODULO", {
            "variable": var_name,
            "operand": value,
            "old_value": old_val,
            "new_value": new_val,
            "variables_after": dict(self.trace.variables)
        })
    
    def _execute_print(self, step: Dict):
        """PRINT output"""
        var_name = step.get("variable")
        message = step.get("message")
        
        if var_name:
            if var_name not in self.trace.variables:
                raise ValueError(f"Variable '{var_name}' not defined")
            output = str(self.trace.variables[var_name])
        elif message is not None:
            output = str(message)
        else:
            output = ""
        
        self.trace.output.append(output)
        self.trace.add_step("PRINT", {
            "output": output,
            "variables_at_print": dict(self.trace.variables)
        })
    
    def _execute_if(self, step: Dict, steps: List, current_idx: int) -> int:
        """Execute IF condition and return index after IF block"""
        condition = step.get("condition")
        
        if not condition:
            raise ValueError("IF requires 'condition' key")
        
        # Evaluate condition
        condition_result = self._evaluate_condition(condition)
        
        self.trace.add_step("IF", {
            "condition": condition,
            "result": condition_result,
            "variables_at_check": dict(self.trace.variables)
        })
        
        if condition_result:
            # Execute IF body
            body_steps = step.get("body", [])
            self._execute_steps(body_steps)
        else:
            # Execute ELSE body if present
            else_body = step.get("else_body", [])
            if else_body:
                self._execute_steps(else_body)
        
        # Move past this IF step
        return current_idx + 1
    
    def _execute_repeat(self, step: Dict, steps: List, current_idx: int) -> int:
        """Execute REPEAT loop"""
        times = step.get("times")
        body_steps = step.get("body", [])
        
        if not times or times <= 0:
            raise ValueError("REPEAT requires positive 'times' value")
        
        if times > self.MAX_ITERATIONS:
            raise ValueError(f"Loop exceeds max iterations ({self.MAX_ITERATIONS})")
        
        for iteration in range(times):
            self.trace.add_step("REPEAT", {
                "iteration": iteration + 1,
                "total_iterations": times,
                "variables_before": dict(self.trace.variables)
            })
            
            self._execute_steps(body_steps)
        
        return current_idx + 1
    
    def _evaluate_condition(self, condition: Dict) -> bool:
        """Evaluate a condition (comparison)"""
        operator = condition.get("operator")
        left_var = condition.get("left")
        right_value = condition.get("right")
        
        if left_var not in self.trace.variables:
            raise ValueError(f"Variable '{left_var}' not defined")
        
        left = self.trace.variables[left_var]
        
        if operator == ">":
            return left > right_value
        elif operator == "<":
            return left < right_value
        elif operator == ">=":
            return left >= right_value
        elif operator == "<=":
            return left <= right_value
        elif operator == "==":
            return left == right_value
        elif operator == "!=":
            return left != right_value
        else:
            raise ValueError(f"Unknown operator: {operator}")


# Test the interpreter
if __name__ == "__main__":
    ir = {
        "steps": [
            {"operation": "SET", "variable": "x", "value": 10},
            {"operation": "ADD", "variable": "x", "value": 5},
            {"operation": "PRINT", "variable": "x"}
        ]
    }
    
    interp = ProgramInterpreter()
    result = interp.execute_ir(ir)
    print(json.dumps(result, indent=2))
