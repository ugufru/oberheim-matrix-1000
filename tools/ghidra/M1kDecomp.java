// Ghidra postScript: decompile functions and write their C pseudocode to files.
// args[0] = output directory; args[1..] = entry addresses (hex, no prefix).
// Each function is written to <outdir>/<name>_<addr>.c, with a header listing
// the functions it calls (so the call graph can be traversed). Writing to files
// avoids the headless logger mangling multi-line output.
//
//   analyzeHeadless build/ghidra m1k -process -noanalysis \
//       -scriptPath tools/ghidra -postScript M1kDecomp.java /abs/out 8003 85E3 84B4
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Function;
import java.io.File;
import java.io.FileWriter;
import java.util.Set;

public class M1kDecomp extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: M1kDecomp <outdir> <addr> [addr...]");
            return;
        }
        File outdir = new File(args[0]);
        outdir.mkdirs();

        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);

        for (int i = 1; i < args.length; i++) {
            long a = Long.parseLong(args[i].replace("0x", "").replace("$", ""), 16);
            Address addr = sp.getAddress(a);
            Function f = getFunctionContaining(addr);
            if (f == null) {
                // Indirectly-called routines may have no Function object yet:
                // disassemble and create one at this address.
                new DisassembleCommand(addr, null, true).applyTo(currentProgram);
                f = createFunction(addr, null);
                if (f == null) {
                    f = getFunctionContaining(addr);
                }
            }
            if (f == null) {
                println("// no function at $" + args[i]);
                continue;
            }
            StringBuilder sb = new StringBuilder();
            sb.append("// ").append(f.getName()).append(" @ ").append(f.getEntryPoint()).append("\n");
            sb.append("// calls:");
            for (Function c : f.getCalledFunctions(monitor)) {
                sb.append(" ").append(c.getName()).append("(").append(c.getEntryPoint()).append(")");
            }
            sb.append("\n\n");

            DecompileResults r = dec.decompileFunction(f, 90, monitor);
            if (r != null && r.decompileCompleted()) {
                sb.append(r.getDecompiledFunction().getC());
            } else {
                sb.append("// decompile failed: ").append(r != null ? r.getErrorMessage() : "null");
            }

            File out = new File(outdir, f.getName() + "_" + f.getEntryPoint() + ".c");
            FileWriter w = new FileWriter(out);
            w.write(sb.toString());
            w.close();
            println("wrote " + out.getPath());
        }
    }
}
