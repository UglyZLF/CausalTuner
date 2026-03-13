# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = -O1 

endif
ifeq ($(CCC_OPTS_ADD),)
 CCC_OPTS_ADD =  -falign-labels -fdevirtualize-speculatively -fgcse-after-reload -fhoist-adjacent-loads -findirect-inlining -finline-functions -fipa-bit-cp -fipa-icf-functions -fipa-ra -fipa-sra -fipa-vrp -fisolate-erroneous-paths-dereference -flra-remat -fpartial-inlining -fpeephole2 -free -frerun-cse-after-loop -fschedule-insns2 -fsplit-loops -fstore-merging -fstrict-aliasing -fstrict-overflow -ftree-loop-vectorize -ftree-partial-pre -ftree-pre -ftree-slp-vectorize -ftree-tail-merge -ftree-vrp 
endif

# Declarations
ifeq ($(ZCC),) 
 ZCC = gcc 
endif
ifeq ($(LDCC),)
 LDCC = gcc
endif
ifeq ($(LD_OPTS),)
 LD_OPTS = -o a.out
endif

# Actions
all:		
	@ $(ZCC) $(CCC_OPTS) $(CCC_OPTS_ADD) -c -w *.c
	@ $(LDCC)  $(LD_OPTS) $(CCC_OPTS_ADD) *.o -lm 

clean:
	@ rm -f a.out *.o *.a *.s *.i *.I
