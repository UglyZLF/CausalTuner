
# Predefined LLVM optimization pipelines (LLVM 17 compatible)
# Loop passes (licm, indvars, loop-rotate, etc.) must be wrapped in loop() within function()

PIPELINES = {
    # 0. [综合优化]
    '0': '-passes=\'function(gvn,instcombine,loop-mssa(licm),simplifycfg,sroa,loop-unroll,early-cse<memssa>,dse,mem2reg,loop(indvars),vector-combine)\'',
    
    # 1. [循环向量化核心]
    '1': '-passes=\'module(elim-avail-extern),function(early-cse<memssa>,instcombine,loop-mssa(licm),simplifycfg,sroa,loop-sink,mem2reg,loop(indvars),speculative-execution,loop-vectorize)\'',
    
    # 2. [参数提升与旋转]
    '2': '-passes=\'cgscc(argpromotion),function(float2int,mem2reg,simplifycfg,sroa,loop-unroll,early-cse<memssa>,instcombine,loop-mssa(licm),early-cse,loop(loop-rotate))\'',
    
    # 3. [SLP 向量化]
    '3': '-passes=\'function(jump-threading,loop-mssa(licm),early-cse<memssa>,instcombine),module(constmerge,strip-dead-prototypes),function(mem2reg,simplifycfg,sroa,loop-unroll,slp-vectorizer)\'',
    
    # 4. [循环加载消除]
    '4': '-passes=\'function(loop-load-elim,mem2reg,simplifycfg,sroa,loop-unroll,early-cse<memssa>,instcombine),module(constmerge),function(lcssa)\'',
    
    # 5. [Profile 导向优化准备]
    '5': '-passes=\'module(cg-profile),function(early-cse<memssa>,instcombine,loop-mssa(licm),simplifycfg,sroa,loop-unroll,mem2reg,reassociate)\'',
    
    # 6. [函数内联准备与调用点分裂]
    '6': '-passes=\'function(mem2reg,simplifycfg,loop-mssa(licm),gvn,instcombine,memcpyopt,early-cse<memssa>,loop(loop-rotate),callsite-splitting,sroa)\'',
    
    # 7. [修正版] (基础清理)
    '7': '-passes=\'function(early-cse,instcombine,loop-mssa(licm),simplifycfg,sroa,loop-sink,mem2reg,reassociate)\'',
    
    # 8. [增强版] (死代码消除)
    '8': '-passes=\'function(sroa,loop-unroll,adce,bdce),module(inferattrs,globaldce)\'',
    
    # 9. [替换版] (强力清理收尾)
    '9': '-passes=\'function(instcombine,simplifycfg,early-cse,dse,dce)\''
}

def get_opt_flags(opt_arg):
    """
    Returns the actual optimization flags.
    If opt_arg is a key in PIPELINES, returns the corresponding pipeline.
    If opt_arg is a sequence of keys (e.g. "0 1"), returns the combined pipelines.
    Otherwise returns opt_arg as is.
    """
    opt_str = str(opt_arg).strip()
    
    # Direct match
    if opt_str in PIPELINES:
        return PIPELINES[opt_str]
        
    # Sequence match (e.g. "0 1")
    parts = opt_str.split()
    if len(parts) > 1:
        # Check if all parts are valid keys
        if all(p in PIPELINES for p in parts):
            # When combining multiple -passes='...', we should strip the outer quotes and -passes= prefix
            # and merge them into a single -passes='...' string?
            # Or just space separate them? opt accepts multiple -passes arguments?
            # opt -passes='A' -passes='B' works? Yes.
            return " ".join([PIPELINES[p] for p in parts])
            
    return opt_arg

