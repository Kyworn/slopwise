// Decompile all functions from a binary using Ghidra Headless.
// @author slopwise
// @category slopwise

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Program;
import java.io.PrintWriter;
import java.io.File;

public class decompile_all extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            println("Usage: decompile_all.java <output_json_path>");
            return;
        }
        
        File outFile = new File(args[0]);
        PrintWriter writer = new PrintWriter(outFile, "UTF-8");

        Program program = getCurrentProgram();
        if (program == null) {
            writer.println("[]");
            writer.close();
            return;
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(program);
        
        FunctionIterator functions = program.getFunctionManager().getFunctions(true);
        
        writer.println("[");
        boolean first = true;
        for (Function func : functions) {
            if (func.isExternal() || func.isThunk()) {
                continue;
            }
            
            DecompileResults decompRes = decompiler.decompileFunction(func, 60, monitor);
            String decompiledCode = "/* Decompilation failed */";
            if (decompRes != null && decompRes.decompileCompleted()) {
                decompiledCode = decompRes.getDecompiledFunction().getC();
            }
            
            if (!first) {
                writer.println(",");
            }
            first = false;
            
            String name = escapeJson(func.getName());
            String signature = escapeJson(func.getPrototypeString(true, true));
            String address = escapeJson(func.getEntryPoint().toString());
            String code = escapeJson(decompiledCode);
            
            writer.println("  {");
            writer.println("    \"name\": \"" + name + "\",");
            writer.println("    \"signature\": \"" + signature + "\",");
            writer.println("    \"address\": \"" + address + "\",");
            writer.println("    \"decompiled\": \"" + code + "\"");
            writer.print("  }");
        }
        writer.println("\n]");
        writer.close();
    }

    private String escapeJson(String input) {
        if (input == null) return "";
        return input.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\b", "\\b")
                    .replace("\f", "\\f")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t");
    }
}
