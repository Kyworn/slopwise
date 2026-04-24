# Decompile all functions from a binary using Ghidra Headless.
# @author slopwise
# @category slopwise
# @keybinding 
# @menupath 
# @toolbar 

import json
import sys
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

def run():
    program = getCurrentProgram()
    if not program:
        print("Error: No program loaded")
        return

    decompiler = DecompInterface()
    decompiler.openProgram(program)
    
    function_manager = program.getFunctionManager()
    functions = function_manager.getFunctions(True) # True = forward
    
    results = []
    monitor = ConsoleTaskMonitor()
    
    for func in functions:
        # Skip external/thunk functions if they don't have code
        if func.isExternal() or func.isThunk():
            continue
            
        decomp_res = decompiler.decompileFunction(func, 60, monitor)
        if decomp_res and decomp_res.decompileCompleted():
            results.append({
                "name": func.getName(),
                "signature": func.getPrototypeString(True, True),
                "decompiled": decomp_res.getDecompiledFunction().getC(),
                "address": func.getEntryPoint().toString()
            })
        else:
            # Fallback for functions that fail to decompile
            results.append({
                "name": func.getName(),
                "signature": func.getPrototypeString(True, True),
                "decompiled": "/* Decompilation failed */",
                "address": func.getEntryPoint().toString(),
                "error": str(decomp_res.getErrorMessage()) if decomp_res else "Unknown error"
            })
            
    # Print the JSON to a marker so we can extract it from the logs
    print("---SLOPWISE-START---")
    print(json.dumps(results, indent=2))
    print("---SLOPWISE-END---")

if __name__ == "__main__":
    run()
