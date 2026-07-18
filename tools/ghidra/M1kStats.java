// Ghidra postScript: report basic analysis coverage for the Matrix-1000 ROM.
// Runs after auto-analysis; prints function/instruction counts so the headless
// pipeline can be sanity-checked from the command line.
//
// @category Matrix1000
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class M1kStats extends GhidraScript {

    @Override
    public void run() throws Exception {
        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();

        long initBytes = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (block.isInitialized()) {
                initBytes += block.getSize();
            }
        }

        println("=== M1000 analysis stats ===");
        println("functions   : " + fm.getFunctionCount());
        println("instructions : " + listing.getNumInstructions());
        println("init bytes   : " + initBytes);
    }
}
