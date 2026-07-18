// Ghidra postScript: print all references TO each address passed as an arg
// (hex, no prefix). Used to find which routines use a string, table, or I/O reg.
//
//   analyzeHeadless build/ghidra m1k -process -noanalysis \
//       -scriptPath tools/ghidra -postScript M1kXrefTo.java b1c4 db3f 2018
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class M1kXrefTo extends GhidraScript {

    @Override
    public void run() throws Exception {
        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        ReferenceManager rm = currentProgram.getReferenceManager();
        for (String s : getScriptArgs()) {
            long a = Long.parseLong(s.replace("0x", "").replace("$", ""), 16);
            println("=== refs to $" + s + " ===");
            ReferenceIterator it = rm.getReferencesTo(sp.getAddress(a));
            int n = 0;
            while (it.hasNext()) {
                Reference r = it.next();
                println("  from " + r.getFromAddress() + "  " + r.getReferenceType());
                n++;
            }
            if (n == 0) {
                println("  (none)");
            }
        }
    }
}
