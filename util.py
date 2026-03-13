from random import randint
from os import system
import numpy as np
import random
import os

cbench = [
    "automotive_susan_c", "automotive_susan_e", "automotive_susan_s", "automotive_bitcount", "bzip2d", "office_rsynth", "telecom_adpcm_c", "telecom_adpcm_d", "security_blowfish_d", "security_blowfish_e", "bzip2e", "telecom_CRC32", "network_dijkstra", "consumer_jpeg_c", "consumer_jpeg_d", "network_patricia", "automotive_qsort1", "security_rijndael_d", "security_rijndael_e", "security_sha", "office_stringsearch1","consumer_lame", "consumer_tiff2bw", "consumer_tiff2rgba", "consumer_tiffdither", "consumer_tiffmedian", 
]
polybench = ["correlation","covariance","2mm","3mm","atax","bicg","doitgen","mvt","gemm","gemver","gesummv","symm","syr2k","syrk","trmm","cholesky","durbin","gramschmidt","lu","ludcmp","trisolv","deriche","floyd-warshall","adi","fdtd-2d","heat-3d","jacobi-1d","jacobi-2d","seidel-2d"]


class Util(object):
    def __init__(self) -> None:
        # self.gcc_flags = ["-falign-labels", "-fcaller-saves", "-fcode-hoisting", "-fcrossjumping", "-fcse-follow-jumps", "-fdevirtualize", "-fdevirtualize-speculatively", "-fexpensive-optimizations", "-fgcse", "-fhoist-adjacent-loads", "-findirect-inlining", "-finline-small-functions", "-fipa-bit-cp", "-fipa-cp", "-fipa-icf", "-fipa-icf-functions", "-fipa-icf-variables", "-fipa-ra", "-fipa-sra", "-fipa-vrp", "-fisolate-erroneous-paths-dereference", "-flra-remat", "-foptimize-sibling-calls", "-foptimize-strlen", "-fpartial-inlining", "-fpeephole2", "-free", "-freorder-blocks-and-partition", "-freorder-functions", "-frerun-cse-after-loop", "-fschedule-insns2", "-fstore-merging", "-fstrict-aliasing", "-fstrict-overflow", "-fthread-jumps", "-ftree-pre", "-ftree-switch-conversion", "-ftree-tail-merge", "-ftree-vrp",]
        self.gcc_flags = self.gain_flags()
        self.baseline = 10
        self.n_flags = len(self.gcc_flags)
        self.times = 0
        # need to revise
        self.o3_baselines = {
            "automotive_susan_c": 1.1955,
            "automotive_susan_e": 0.671,
            "automotive_susan_s": 1.0065,
            "automotive_bitcount": 2.203,
            "bzip2d": 0.7675,
            "office_rsynth": 0.564,
            "telecom_adpcm_c": 1.854,
            "telecom_adpcm_d": 0.921,
            "security_blowfish_d": 1.9685,
            "security_blowfish_e": 1.996,
            "bzip2e": 1.087,
            "telecom_CRC32": 1.5655,
            "network_dijkstra": 1.7935,
            "consumer_jpeg_c": 0.541,
            "consumer_jpeg_d": 0.378,
            "network_patricia": 1.803,
            "automotive_qsort1": 0.8675,
            "security_rijndael_d": 2.2215,
            "security_rijndael_e": 2.175,
            "security_sha": 1.0445,
            "office_stringsearch1": 1.0955,
            "consumer_tiff2bw": 0.259,
            "consumer_tiff2rgba": 0.263,
            "consumer_tiffdither": 0.3895,
            "consumer_tiffmedian": 0.1915,
            "correlation": 8.253, 
            "covariance": 8.3475,  
            "3mm": 3.0885,        
            "2mm": 1.6735,
            "bicg": 0.0455,
            "symm": 3.1745
        }


    def gain_flags(self):
       

        flags = ['-tti', '-tbaa', '-scoped-noalias-aa', '-assumption-cache-tracker', '-targetlibinfo', '-verify', '-lower-expect', '-simplifycfg', '-domtree', '-sroa', '-early-cse', '-profile-summary-info', '-annotation2metadata', '-forceattrs', '-inferattrs', '-callsite-splitting', '-ipsccp', '-called-value-propagation', '-globalopt', '-mem2reg', '-deadargelim', '-basic-aa', '-aa', '-loops', '-lazy-branch-prob', '-lazy-block-freq', '-opt-remark-emitter', '-instcombine', '-basiccg', '-globals-aa', '-prune-eh', '-inline', '-openmp-opt-cgscc', '-function-attrs', '-argpromotion', '-memoryssa', '-early-cse-memssa', '-speculative-execution', '-lazy-value-info', '-jump-threading', '-correlated-propagation', '-aggressive-instcombine', '-libcalls-shrinkwrap', '-postdomtree', '-branch-prob', '-block-freq', '-pgo-memop-opt', '-tailcallelim', '-reassociate', '-loop-simplify', '-lcssa-verification', '-lcssa', '-scalar-evolution', '-licm', '-loop-rotate', '-loop-unswitch', '-loop-idiom', '-indvars', '-loop-deletion', '-loop-unroll', '-mldst-motion', '-phi-values', '-memdep', '-gvn', '-sccp', '-demanded-bits', '-bdce', '-adce', '-memcpyopt', '-dse', '-barrier', '-elim-avail-extern', '-rpo-function-attrs', '-globaldce', '-float2int', '-lower-constant-intrinsics', '-loop-accesses', '-loop-distribute', '-inject-tli-mappings', '-loop-vectorize', '-loop-load-elim', '-slp-vectorizer', '-vector-combine', '-transform-warning', '-alignment-from-assumptions', '-strip-dead-prototypes', '-constmerge', '-cg-profile', '-loop-sink', '-instsimplify', '-div-rem-pairs', '-annotation-remarks']
        
        # Remove analysis passes from the pool
        analysis_passes = ['-tti', '-tbaa', '-basic-aa', '-aa', '-globals-aa', '-memoryssa', '-demanded-bits', '-scalar-evolution', '-lazy-value-info', '-lazy-branch-prob', '-lazy-block-freq', '-opt-remark-emitter', '-targetlibinfo', '-assumption-cache-tracker', '-profile-summary-info', '-verify', '-domtree', '-postdomtree', '-branch-prob', '-block-freq', '-memdep', '-loops', '-phi-values']
        
        # Also remove early-cse-memssa and lcssa-verification which are analysis/utility
        analysis_passes.extend(['-early-cse-memssa', '-lcssa-verification', '-basiccg'])

        valid_flags = [f for f in flags if f not in analysis_passes]
        
        # Ensure we have at least 2 flags to avoid random.randrange(1, 0) error
        # This is critical for EnhancedHybridGA.py which does: pt = random.randint(1, self.total_dims-1)
        if len(valid_flags) < 2:
            print(f"Warning: Only {len(valid_flags)} valid flags found. Adding dummies.")
            # Add some dummy safe flags if we stripped too many (unlikely but safe)
            while len(valid_flags) < 2:
                valid_flags.append("-instcombine") 
                
        return valid_flags

        # res = "-slp-vectorizer -basiccg -loop-simplify -gvn -globaldce -lazy-value-info -simplifycfg -early-cse -domtree -loops -verify -memdep -loop-vectorize -mem2reg -memcpyopt -forceattrs -bdce -jump-threading -correlated-propagation -loop-accesses -block-freq -scalar-evolution -sroa -instcombine -strip -bounds-checking -insert-gcov-profiling -targetlibinfo -demanded-bits -strip-nondebug -da -nvvm-reflect -scalarizer -objc-arc-expand -amdgpu-annotate-uniform -intervals -rewrite-symbols -reg2mem -nary-reassociate -divergence -dce -external-aa -module-debuginfo -slsr -loop-interchange -cross-dso-cfi -loweratomic -alloca-hoisting -instsimplify -instcount -separate-const-offset-from-gep -pgo-instr-gen -codegenprepare -consthoist -instnamer -mergefunc -loop-reduce -cost-model -slp-vectorizer -basiccg -loop-simplify -gvn -globaldce -lazy-value-info -simplifycfg -early-cse -domtree -loops -verify -memdep -loop-vectorize -mem2reg -memcpyopt -forceattrs -bdce -jump-threading -correlated-propagation -loop-accesses -block-freq -scalar-evolution -sroa -instcombine"
        # flags = res.split(" ")
        # print(flags)
        # return flags

    def gain_baseline(self,suite_name):
        path = self.testsuite_path(suite_name)
        self.update_makefile(path," ","-O1 ","./data/Makefile2.llvm")
        O1 = self.get_runtime(path,suite_name)

        self.update_makefile(path," ","-O2 ","./data/Makefile2.llvm" )
        O2 = self.get_runtime(path,suite_name)

        self.update_makefile(path," ","-O3 ","./data/Makefile2.llvm" )
        O3 = self.get_runtime(path,suite_name)

        print("{} {} {} {}".format(suite_name,O1,O2,O3))

    def gain_baseline_O3(self,suite_name):
        path = self.testsuite_path(suite_name)
        option = self.testsuite_option(suite_name)
        
        self.update_makefile(path, option, "-O3 ","./data/Makefile2.llvm" )
        # self.update_makefile(path," ","-O3 ","./data/Makefile2.llvm" )
        o3_speed = []
        for _ in range(5):
            O3 = self.get_runtime(path,suite_name)
            o3_speed.append(O3)

        final_O3 = np.median(o3_speed)
        print(suite_name)
        print(final_O3)
        return final_O3
    # 越界修改
    def boundary(self,x,n_max=1,n_min=0):
        if x < n_min:
            return n_min
        if x > n_max:
            return n_max
        return x

    
    def init_position(self,N):

        seed = np.random.RandomState(456)  
        # seed = np.random.RandomState(8)
        X = seed.random((N, self.n_flags))
        
        return X

    
    def binary_conversion(self,pops,thres = 0.5):
        size = len(pops)
        # print(pops,size)
        pop_bin = np.zeros([size, self.n_flags], dtype='int')
        
        for i in range(size):
            for d in range(self.n_flags):
                if pops[i,d] > thres:
                    pop_bin[i,d] = 1
                else:
                    pop_bin[i,d] = 0
        return pop_bin
    
    
    def testsuite_option(self,file_folder):
        if file_folder in polybench:
            return  " -I ../utilities ../utilities/polybench.c " 
        if file_folder == "consumer_lame":
            return " -DLAMESNDFILE -DHAVEMPGLIB -DLAMEPARSE "

        return ""
    

    
    def testsuite_path(self,file_folder):
        if file_folder in polybench:
            path = "./testsuite/" + file_folder 
        else:
            path = "./testsuite/" + file_folder + "/src"
        return path


    def update_makefile(self, path, option, opt_level, makefile="./data/Makefile.llvm"):
        f = open(os.path.join(path, "Makefile"), "w")
        with open(os.path.join(makefile), "r") as g:
            while 1:
                line = g.readline()
                if line == "":
                    break
                elif "@ $(OPT) $(CCC_OPTS_ADD) tmp.bc -o tmp.bc" in line:
                   
                    line = "\t@ $(OPT) $(CCC_OPTS_ADD) tmp.bc -o tmp.bc -enable-new-pm=0 \n"
                elif "CCC_OPTS_ADD =" in line:
                    line = line.strip("\n") + opt_level + " \n"
                elif " CC_OPTS =" in line:
                    line = line.strip("\n") + " \n"
                elif "CCC_OPTS = \n" in line:
                    line = line.strip("\n") + option + "\n"
                elif "@ $(LDCC) tmp.bc $(LD_OPTS)" in line:
                    line = line + '\n' + '\t' + "@ mv a.out a.bc" +'\n' +'\t' + "@ $(ZCC) a.bc -lm -o a.out" +'\n'
                f.writelines(line)
        f.close()
    def get_o3_baseline(self, suite_name):
        
        if suite_name in self.o3_baselines:
            return self.o3_baselines[suite_name]
        
        print(f"Baseline for {suite_name} not found, measuring now...")
        # 调用你原有的函数测量 O3
        baseline = self.gain_baseline_O3(suite_name)
        self.o3_baselines[suite_name] = baseline
        return baseline

    def run_procedure(self, suite_name, flags=None):
        path = self.testsuite_path(suite_name)
        option = self.testsuite_option(suite_name)
        
      
        baseline = self.get_o3_baseline(suite_name)

       
        if flags is None:
            return baseline

        # 2. 拼接当前待测试的编译参数
        opt_level = "" 
        for i, flag in enumerate(flags):
            if flag:
                print(f"[DEBUG] Current Flags being tested: {opt_level}")
                opt_level += self.gcc_flags[i] + " "

        # 3. 运行测试（通常测3次取中位数以减小误差）
        speedups = []
        self.update_makefile(path, option, opt_level)
        for _ in range(5):
            # 仅编译当前 flags 组合
            run_time = self.get_runtime(path, suite_name)
            speedup = baseline / run_time
            speedups.append(speedup)
        
        final_speedup = np.median(speedups)
        print(f"Program: {suite_name} | Speedup: {final_speedup:.4f}x")
        
        
        return -final_speedup


    def run_procedure2(self,suite_name,flags=None):

        path = self.testsuite_path(suite_name)
        option = self.testsuite_option(suite_name)
        # print(flags)
        print(flags)
        if flags is not None :
            opt_level = ""
            # opt_level = " ".join(flags) + " "
            opt_level = " ".join(map(str, flags)) + " "
            # for flag in flags:
            #     opt_level += flag + " "
        else:
            opt_level = "-O3 "
            self.update_makefile(path,option,opt_level,"./data/Makefile2.llvm")
            return self.get_runtime(path,suite_name)
        print("opt_level = {}".format(opt_level))
        speedups = []
        for _ in range(1):
            # print(opt_level)
            
            self.update_makefile(path,option,opt_level)
          
            run_time = self.get_runtime(path,suite_name)
            print("opt run_time")
            print(run_time)
            
       
            self.update_makefile(path,option,"-O3 " )
            baseline = self.get_runtime(path,suite_name)

            print("O3 run_time")
            print(baseline)
            speedups.append(baseline/run_time)
        
        print("Speedup={}".format(np.median(speedups)))
        speedup = -np.median(speedups)
  
        return speedup
  
    def run_procedure_runtime(self,suite_name,flags=None):
    
        path = self.testsuite_path(suite_name)
        option = self.testsuite_option(suite_name)
    
        if flags is not None :
            opt_level = ""
            # opt_level = " ".join(flags) + " "
            opt_level = " ".join(map(str, flags)) + " "
            # for flag in flags:
            #     opt_level += flag + " "
        else:
            opt_level = "-O3 "
            self.update_makefile(path,option,opt_level,"./data/Makefile2.llvm")
            return self.get_runtime(path,suite_name)
        print("opt_level = {}".format(opt_level))
        speedups = []
        run_times = []
        for _ in range(1):
           
            self.update_makefile(path,option,opt_level)
            run_time = self.get_runtime(path,suite_name)
            
            run_times.append(run_time)
        # print("option={}",option)
        print("run_time={}".format(np.median(run_times)))
        
  
        return run_time
    
    def run_procedure_runtime(self,suite_name,flags=None):
    
        path = self.testsuite_path(suite_name)
        option = self.testsuite_option(suite_name)
      
        if flags is not None :
            opt_level = ""
            
            opt_level = " ".join(map(str, flags)) + " "

        else:
            opt_level = "-O3 "
            self.update_makefile(path,option,opt_level,"./data/Makefile2.llvm")
            return self.get_runtime(path,suite_name)
        print("opt_level = {}".format(opt_level))
        speedups = []
        run_times = []
        for _ in range(1):
            
            self.update_makefile(path,option,opt_level)
            
            run_time = self.get_runtime(path,suite_name)
            run_times.append(run_time)
        # print("option={}",option)
        print("run_time={}".format(np.median(run_times)))
       
  
        return run_time
        
    def get_runtime(self,path,suite_name):
        run_time = 0

        if os.path.exists(os.path.join(path, "a.out") ) or os.path.exists(os.path.join(path, "tmp.bc") ) :
            os.system("cd {} && make clean".format(path))
        #编译程序
        os.system("cd {} && make ".format(path))

        if suite_name in polybench:
            command = "cd {} && chmod +x a.out && " \
            "bash -c '(TIMEFORMAT=\"%3R\"; time taskset -c 0 ./a.out  > output.txt) &> time.txt'".format(path)  # runtime will be wrote in "time.txt"
            os.system(command=command)#只执行并输出到控制台
        else : # for cBench
            command = "cd {} && chmod +x a.out && chmod +x ./__run  &&" \
            "bash -c '(TIMEFORMAT=\"%3R\"; time taskset -c 0 ./__run 1  > output.txt) &> time.txt'".format(path) # runtime will be wrote in "time.txt"
            os.system(command=command)

        try:
            with open(path + "/time.txt", "r") as file:
                content = file.read().strip()
                lines = content.split('\n')
                
                found = False
                # Strategy 1: Try to parse a line as a simple float (expected if TIMEFORMAT works)
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        run_time = float(line)
                        found = True
                        break
                    except ValueError:
                        pass
                
                # Strategy 2: Parse standard time output (real XmYs) if Strategy 1 failed
                if not found:
                    for line in lines:
                        if "real" in line:
                            # Format usually: real 0m0.123s (tab or space separated)
                            parts = line.split()
                            if len(parts) >= 2:
                                time_str = parts[1]
                                if 'm' in time_str and time_str.endswith('s'):
                                    try:
                                        m_split = time_str.split('m')
                                        minutes = float(m_split[0])
                                        seconds = float(m_split[1][:-1])
                                        run_time = minutes * 60 + seconds
                                        found = True
                                        break
                                    except ValueError:
                                        pass

                # if not found:
                #     print(f"Warning: Unexpected time.txt format for {suite_name}: {content}")
                #     run_time = 1000.0

        except Exception as e:
            print(f"Error reading runtime for {suite_name}: {e}")
            run_time = 1000.0

        return run_time

    