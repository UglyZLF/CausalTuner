# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = -O1 

endif
ifeq ($(CCC_OPTS_ADD),)
 CCC_OPTS_ADD =  -fcrossjumping -fcse-follow-jumps -fgcse -fgcse-after-reload -fhoist-adjacent-loads -finline-small-functions -fipa-cp-clone -fipa-ra -fipa-sra -fisolate-erroneous-paths-dereference -foptimize-strlen -fpredictive-commoning -free -freorder-blocks-and-partition -fstore-merging -fstrict-aliasing -ftree-partial-pre -ftree-pre -ftree-slp-vectorize 
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
