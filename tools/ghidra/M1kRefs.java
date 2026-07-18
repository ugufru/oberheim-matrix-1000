// Ghidra postScript: extract every reference from analyzed code to a non-ROM
// address (< $8000) — i.e. RAM variables and memory-mapped I/O registers.
//
// This is the empirical evidence for the memory/IO map: which addresses the
// firmware actually reads and writes, with access counts and a sample call
// site. Run against the already-analyzed project (no re-import):
//
//   analyzeHeadless build/ghidra m1k -process -noanalysis \
//       -scriptPath tools/ghidra -postScript M1kRefs.java
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.RefType;
import java.util.Map;
import java.util.TreeMap;

public class M1kRefs extends GhidraScript {

    private static class Acc {
        long reads = 0, writes = 0, other = 0;
        Address sample = null;
    }

    @Override
    public void run() throws Exception {
        Listing listing = currentProgram.getListing();
        TreeMap<Long, Acc> map = new TreeMap<>();

        InstructionIterator it = listing.getInstructions(true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            for (Reference r : ins.getReferencesFrom()) {
                Address to = r.getToAddress();
                if (to == null || !to.isMemoryAddress()) {
                    continue;
                }
                long a = to.getOffset();
                if (a >= 0x8000) {
                    continue; // ROM / code target, not RAM or I/O
                }
                Acc acc = map.get(a);
                if (acc == null) {
                    acc = new Acc();
                    acc.sample = ins.getAddress();
                    map.put(a, acc);
                }
                RefType rt = r.getReferenceType();
                if (rt.isWrite()) {
                    acc.writes++;
                } else if (rt.isRead()) {
                    acc.reads++;
                } else {
                    acc.other++;
                }
            }
        }

        println("=== non-ROM references (addr  R/W/other  sampleSite) ===");
        println(String.format("%-6s %5s %5s %5s   %s", "addr", "rd", "wr", "oth", "sample"));
        for (Map.Entry<Long, Acc> e : map.entrySet()) {
            Acc a = e.getValue();
            println(String.format("$%04X  %5d %5d %5d   @%s",
                    e.getKey(), a.reads, a.writes, a.other, a.sample));
        }
        println("=== distinct non-ROM addresses: " + map.size() + " ===");
    }
}
