from enum import Enum

class Actions(Enum):
    # ==============================================================================
    # Module Optimization Passes (跨函数全局优化)
    # ==============================================================================
    AlwaysInline = "module(always-inline)"
    Attributor = "module(attributor)"
    CalledValuePropagation = "module(called-value-propagation)"
    CanonicalizeAliases = "module(canonicalize-aliases)"
    ConstMerge = "module(constmerge)"
    CoroEarly = "module(coro-early)"
    CoroCleanup = "module(coro-cleanup)"
    DeadArgElim = "module(deadargelim)"
    ElimAvailExtern = "module(elim-avail-extern)"
    ForceAttrs = "module(forceattrs)"
    GlobalDCE = "module(globaldce)"
    GlobalOpt = "module(globalopt)"
    GlobalSplit = "module(globalsplit)"
    HotColdSplit = "module(hotcoldsplit)"
    InferAttrs = "module(inferattrs)"
    InlinerWrapper = "module(inliner-wrapper)"
    Ipsccp = "module(ipsccp)" # 进程间稀疏条件常量传播
    LowerGlobalDtors = "module(lower-global-dtors)"
    MergeFunc = "module(mergefunc)"
    OpenmpOpt = "module(openmp-opt)"
    PartialInliner = "module(partial-inliner)"
    RelLookupTableConverter = "module(rel-lookup-table-converter)"
    RpoFunctionAttrs = "module(rpo-function-attrs)"
    SccOzModuleInliner = "module(scc-oz-module-inliner)"
    SyntheticCountsPropagation = "module(synthetic-counts-propagation)"
    WholeProgramDevirt = "module(wholeprogramdevirt)"

    # ==============================================================================
    # CGSCC Optimization Passes (调用图强连通分量优化)
    # ==============================================================================
    ArgPromotion = "cgscc(argpromotion)"
    FunctionAttrs = "cgscc(function-attrs)"
    AttributorCgscc = "cgscc(attributor-cgscc)"
    OpenmpOptCgscc = "cgscc(openmp-opt-cgscc)"

    # ==============================================================================
    # Function Optimization Passes (单函数局部优化)
    # ==============================================================================
    Adce = "function(adce)" # 侵略性死代码消除
    AggressiveInstCombine = "function(aggressive-instcombine)"
    AlignmentFromAssumptions = "function(alignment-from-assumptions)"
    Bdce = "function(bdce)" # 位级死代码消除
    CallsiteSplitting = "function(callsite-splitting)"
    ConstHoist = "function(consthoist)"
    ConstraintElimination = "function(constraint-elimination)"
    Chr = "function(chr)" # 控制流分级归约
    CoroElide = "function(coro-elide)"
    CorrelatedPropagation = "function(correlated-propagation)"
    Dce = "function(dce)"
    DfaJumpThreading = "function(dfa-jump-threading)"
    DivRemPairs = "function(div-rem-pairs)"
    Dse = "function(dse)" # 死存储消除
    FixIrreducible = "function(fix-irreducible)"
    FlattenCfg = "function(flattencfg)"
    Float2Int = "function(float2int)"
    GuardWideningFunc = "function(guard-widening)"
    GvnHoist = "function(gvn-hoist)"
    GvnSink = "function(gvn-sink)"
    InferAddressSpaces = "function(infer-address-spaces)"
    InstCombine = "function(instcombine)"
    InstSimplify = "function(instsimplify)"
    Irce = "function(irce)"
    JumpThreading = "function(jump-threading)"
    LibcallsShrinkwrap = "function(libcalls-shrinkwrap)"
    LoadStoreVectorizer = "function(load-store-vectorizer)"
    LoopSimplify = "function(loop-simplify)"
    LoopSink = "function(loop-sink)"
    LowerAtomic = "function(loweratomic)"
    LowerExpect = "function(lower-expect)"
    LowerGuardIntrinsic = "function(lower-guard-intrinsic)"
    LowerConstantIntrinsics = "function(lower-constant-intrinsics)"
    LowerWidenableCondition = "function(lower-widenable-condition)"
    LowerInvoke = "function(lowerinvoke)"
    LowerSwitch = "function(lowerswitch)"
    Mem2Reg = "function(mem2reg)"
    MemCpyOpt = "function(memcpyopt)"
    MergeIcmps = "function(mergeicmps)"
    MergeReturn = "function(mergereturn)"
    NaryReassociate = "function(nary-reassociate)"
    NewGvn = "function(newgvn)"
    PartiallyInlineLibcalls = "function(partially-inline-libcalls)"
    PgoMemopOpt = "function(pgo-memop-opt)"
    Reassociate = "function(reassociate)"
    Scalarizer = "function(scalarizer)"
    Sccp = "function(sccp)"
    SeparateConstOffsetFromGep = "function(separate-const-offset-from-gep)"
    Sink = "function(sink)"
    SlpVectorizer = "function(slp-vectorizer)"
    Slsr = "function(slsr)" # 直线标量强度削减
    SpeculativeExecution = "function(speculative-execution)"
    Sroa = "function(sroa)"
    TailCallElim = "function(tailcallelim)"
    Tlshoist = "function(tlshoist)"
    VectorCombine = "function(vector-combine)"

    # ==============================================================================
    # Loop Optimization Passes (循环优化)
    # ==============================================================================
    LoopFlatten = "function(loop(loop-flatten))"
    LoopInterchange = "function(loop(loop-interchange))"
    LoopUnrollAndJam = "function(loop(loop-unroll-and-jam))"
    LoopIdiom = "function(loop(loop-idiom))"
    LoopInstSimplify = "function(loop(loop-instsimplify))"
    LoopRotate = "function(loop(loop-rotate))"
    LoopDeletion = "function(loop(loop-deletion))"
    LoopSimplifycfg = "function(loop(loop-simplifycfg))"
    LoopReduce = "function(loop(loop-reduce))"
    IndVars = "function(loop(indvars))"
    LoopUnrollFull = "function(loop(loop-unroll-full))"
    LoopPredication = "function(loop(loop-predication))"
    GuardWideningLoop = "function(loop(guard-widening))"
    LoopBoundSplit = "function(loop(loop-bound-split))"
    LoopReroll = "function(loop(loop-reroll))"
    LoopVersioningLicm = "function(loop(loop-versioning-licm))"
    Licm = "function(loop-mssa(licm))" # 循环不变代码外提