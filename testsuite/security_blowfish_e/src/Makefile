# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = 
endif
ifeq ($(CCC_OPTS_ADD),)
  CCC_OPTS_ADD =  -scoped-noalias-aa -lower-expect -sroa -annotation2metadata -forceattrs -inferattrs -callsite-splitting -called-value-propagation -globalopt -deadargelim -instcombine -prune-eh -openmp-opt-cgscc -argpromotion -speculative-execution -correlated-propagation -libcalls-shrinkwrap -pgo-memop-opt -tailcallelim -reassociate -loop-simplify -lcssa -loop-idiom -loop-unroll -gvn -sccp -adce -barrier -elim-avail-extern -rpo-function-attrs -float2int -inject-tli-mappings -loop-vectorize -loop-load-elim -slp-vectorizer -vector-combine -transform-warning -strip-dead-prototypes -div-rem-pairs -annotation-remarks  
endif

# Declarations
ifeq ($(LLVM_BIN),)
 LLVM_BIN = /data/llvm14_0_0/bin
endif
ifeq ($(ZCC),) 
 ZCC = $(LLVM_BIN)/clang 
endif
ifeq ($(CC_OPTS),)
 CC_OPTS = -emit-llvm -Xclang -disable-O0-optnone  
endif
ifeq ($(LDCC),)
 LDCC = $(LLVM_BIN)/llvm-link 
endif
ifeq ($(OPT),)
 OPT = $(LLVM_BIN)/opt
endif
ifeq ($(LD_OPTS),)
 LD_OPTS = -f -o a.out
endif

# Actions
all:		
	@ $(ZCC) $(CCC_OPTS) $(CC_OPTS) -Wl -w -c *.c
	@ $(LDCC) *.bc -o tmp.bc
	@ $(OPT) $(CCC_OPTS_ADD) tmp.bc -o tmp.bc -enable-new-pm=0 
	@ $(LDCC) tmp.bc $(LD_OPTS) 

	@ mv a.out a.bc
	@ $(ZCC) a.bc -lm -o a.out
clean:
	@ rm -f a.out *.o *.a *.s *.i *.I *.bc *.ll
