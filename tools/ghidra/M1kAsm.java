// Ghidra postScript: dump a raw disassembly listing for an address range.
// args: <start-hex> <end-hex>. Prints "addr  bytes  mnemonic operands" one
// instruction per line (single-line prints survive the headless logger). Any
// gap with no instruction is disassembled first so control flow is visible.
//
//   analyzeHeadless build/ghidra m1k -process -noanalysis \
//       -scriptPath tools/ghidra -postScript M1kAsm.java 8302 8360
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;

public class M1kAsm extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        long start = Long.parseLong(args[0].replace("0x", "").replace("$", ""), 16);
        long end = Long.parseLong(args[1].replace("0x", "").replace("$", ""), 16);
        Listing listing = currentProgram.getListing();

        // Ensure the range is disassembled.
        Address a = sp.getAddress(start);
        while (a.getOffset() <= end) {
            if (listing.getInstructionAt(a) == null) {
                new DisassembleCommand(a, null, false).applyTo(currentProgram);
            }
            Instruction ins = listing.getInstructionAt(a);
            if (ins == null) {
                a = a.add(1);
                continue;
            }
            a = ins.getMaxAddress().add(1);
        }

        Instruction ins = listing.getInstructionAt(sp.getAddress(start));
        while (ins != null && ins.getAddress().getOffset() <= end) {
            StringBuilder b = new StringBuilder();
            for (byte x : ins.getBytes()) {
                b.append(String.format("%02X", x & 0xFF));
            }
            println(String.format("%s  %-10s %s", ins.getAddress(), b.toString(), ins.toString()));
            ins = ins.getNext();
        }
    }
}
