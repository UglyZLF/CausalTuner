# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = -O1  -I. -I../utilities ../utilities/polybench.c

endif
ifeq ($(CCC_OPTS_ADD),)
 CCC_OPTS_ADD =  -falign-labels -fcaller-saves -fcode-hoisting -fcrossjumping -fcse-follow-jumps -fdevirtualize -fdevirtualize-speculatively -fhoist-adjacent-loads -finline-small-functions -fipa-cp -fipa-icf-functions -fipa-ra -fipa-vrp -fpartial-inlining -fpeel-loops -fpeephole2 -free -freorder-blocks-and-partition -freorder-functions -fsplit-loops -fstore-merging -fstrict-aliasing -ftree-loop-distribute-patterns -ftree-loop-vectorize -ftree-slp-vectorize -ftree-tail-merge -ftree-vrp -funswitch-loops 
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
