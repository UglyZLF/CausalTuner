# ************ CCC - passing optimization flags ************ 
ifeq ($(CCC_OPTS),)
 CCC_OPTS = 
endif
ifeq ($(CCC_OPTS_ADD),)
  CCC_OPTS_ADD =  -scoped-noalias-aa -lower-expect -simplifycfg -sroa -early-cse -annotation2metadata -forceattrs -inferattrs -callsite-splitting -ipsccp -called-value-propagation -globalopt -deadargelim -instcombine -prune-eh -inline -openmp-opt-cgscc -function-attrs -argpromotion -speculative-execution -jump-threading -correlated-propagation -aggressive-instcombine -libcalls-shrinkwrap -pgo-memop-opt -tailcallelim -reassociate -loop-simplify -lcssa -licm -loop-rotate -loop-unswitch -loop-idiom -indvars -loop-deletion -loop-unroll -mldst-motion -gvn -sccp -bdce -adce -memcpyopt -barrier -elim-avail-extern -rpo-function-attrs -globaldce -float2int -lower-constant-intrinsics -loop-distribute -inject-tli-mappings -loop-vectorize -slp-vectorizer -vector-combine -transform-warning -alignment-from-assumptions -strip-dead-prototypes -constmerge -cg-profile -instsimplify -div-rem-pairs  
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
