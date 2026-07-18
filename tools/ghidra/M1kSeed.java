// Ghidra preScript: seed the Matrix-1000 6809 entry points before auto-analysis.
//
// A raw ROM has no format metadata, so Ghidra doesn't know where code starts.
// We read the 6809 hardware vector table ($FFF0-$FFFF, big-endian words),
// disassemble each vector target that lands in ROM ($8000-$FFFF), and create a
// named function there. Auto-analysis then follows calls/jumps from these roots.
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.listing.Function;

public class M1kSeed extends GhidraScript {

    private AddressSpace space;
    private Memory mem;

    private Address addr(long x) {
        return space.getAddress(x);
    }

    private int word(long a) throws Exception {
        int hi = mem.getByte(addr(a)) & 0xFF;
        int lo = mem.getByte(addr(a + 1)) & 0xFF;
        return (hi << 8) | lo;
    }

    @Override
    public void run() throws Exception {
        space = currentProgram.getAddressFactory().getDefaultAddressSpace();
        mem = currentProgram.getMemory();

        String[] names = {"vec_FIRQ", "vec_IRQ", "vec_SWI", "vec_NMI", "vec_RESET"};
        long[] vaddrs = {0xFFF6L, 0xFFF8L, 0xFFFAL, 0xFFFCL, 0xFFFEL};

        for (int i = 0; i < names.length; i++) {
            int target = word(vaddrs[i]);
            // $FFFF is the unused-vector sentinel (SWI/NMI/SWI2/SWI3 are unused
            // on the Matrix-1000); anything outside ROM is likewise not code.
            if (target < 0x8000 || target >= 0xFFF0) {
                println(String.format("skip %s -> $%04X (unused/outside ROM)", names[i], target));
                continue;
            }
            Address a = addr(target);
            new DisassembleCommand(a, null, true).applyTo(currentProgram);
            Function fn = createFunction(a, names[i]);
            println(String.format("seeded %-9s @ $%04X  (function: %b)", names[i], target, fn != null));
        }
    }
}
