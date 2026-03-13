# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = -O1 

endif
ifeq ($(CCC_OPTS_ADD),)
 CCC_OPTS_ADD =  -fcode-hoisting -fcrossjumping -fdevirtualize -fexpensive-optimizations -fgcse -fgcse-after-reload -fhoist-adjacent-loads -findirect-inlining -finline-functions -fipa-bit-cp -fipa-cp -fipa-icf -fipa-icf-functions -fipa-ra -fisolate-erroneous-paths-dereference -flra-remat -foptimize-sibling-calls -foptimize-strlen -fpartial-inlining -fpeel-loops -fpeephole2 -fpredictive-commoning -fschedule-insns2 -fstrict-aliasing -fstrict-overflow -fthread-jumps -ftree-loop-vectorize -ftree-pre -ftree-tail-merge 
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
