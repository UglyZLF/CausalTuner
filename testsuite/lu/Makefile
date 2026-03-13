# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS =  
endif
ifeq ($(CCC_OPTS_ADD),)
  CCC_OPTS_ADD =  -O3  
endif

# Declarations
ifeq ($(LLVM_BIN),)
 LLVM_BIN = /data/llvm14_0_0/bin
endif
ifeq ($(ZCC),) 
 ZCC = $(LLVM_BIN)/clang 
endif
ifeq ($(CC_OPTS),)
 CC_OPTS =  
endif
ifeq ($(LDCC),)
 LDCC = $(LLVM_BIN)/llvm-link 
endif
ifeq ($(LD_OPTS),)
 LD_OPTS = -f -o a.out
endif

# Actions
all:		
	@ $(ZCC) $(CCC_OPTS) $(CCC_OPTS_ADD) -Wl -lm -w  *.c

clean:
	@ rm -f a.out *.o *.a *.s *.i *.I *.bc *.ll
