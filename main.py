# from algorithm.BA import BA
# from algorithm.CS import CS
# from algorithm.DE import DE
# from algorithm.EDA import EDA
# from algorithm.FA import FA
# from algorithm.FPA import FPA
# from algorithm.GWO import GWO
# from algorithm.HHO import HHO
# from algorithm.JAYA import JAYA
# from algorithm.PSO import PSO
# from algorithm.SCA import SCA
# from algorithm.SSA import SSA
# from algorithm.WOA import WOA
from algorithm.NevergradAlg import NevergradAlg 
from algorithm.GroupTunerAlg import GroupTunerAlg
from algorithm.CausalGuidedGA import CausalGuidedGA 
from algorithm.GA import GA
from algorithm.GAnew import GAnew
from util import *
from os import system
import argparse
import time 
from tqdm import tqdm
import json

help_string = "Usage:"

# polybench时间太长，平时测试先不用
cbench = [
    "automotive_susan_c", "automotive_susan_e", "automotive_susan_s", "automotive_bitcount", "bzip2d", "office_rsynth", "telecom_adpcm_c", "telecom_adpcm_d", "security_blowfish_d", "security_blowfish_e", "bzip2e", "telecom_CRC32", "network_dijkstra", "consumer_jpeg_c", "consumer_jpeg_d", "network_patricia", "automotive_qsort1", "security_rijndael_d", "security_rijndael_e", "security_sha", "office_stringsearch1", "consumer_tiff2bw", "consumer_tiff2rgba", "consumer_tiffdither", "consumer_tiffmedian", 
]
polybench = ["correlation","covariance","3mm","2mm","bicg","symm"]#,"correlation","covariance","2mm","3mm","atax","bicg","doitgen","mvt","gemm","gemver","gesummv","cholesky","durbin","gramschmidt","lu","ludcmp","trisolv","deriche","floyd-warshall","adi","fdtd-2d","heat-3d","jacobi-1d","jacobi-2d","seidel-2d"]
testsuite =polybench  #cbench + 


# 所有已经支持的算法，但部分存在BUG
# algorithm = ["BA", "CS", "DE", "EDA", "FA", "FPA", "GA",
#                 "GWO", "HHO", "JAYA", "PSO", "SCA", "SSA", "WOA"]
algorithm = ["GA"]#"DE", "EDA", "GA","BA", "CS", "FA", "FPA", "JAYA", "PSO", "SCA"

opts = ["-O0","-O1","-O2","-O3"]



def select_flags(alg_name,floder_name,n_pop=10,n_gen=30):

    parameter = "\"{}\",{},{}".format(floder_name,n_pop,n_gen)
    func = "{}({})".format(alg_name,parameter)
    # print(func)

    result_file = "./result/txt/{}_{}.txt".format(alg_name,floder_name)

    #if os.path.exists(result_file):
        #return
    init_time = time.time()

    model = eval(func)

    [best_flags, min_time], times = model.start()
    cost_time = time.time() - init_time
    curve = model.curve.tolist()
    best_flags = best_flags.tolist()

    content = "algorithm:{}\nbenchmark:{}\ngenerate:{}\npopulation:{}\ncurve:{}\nbest_flags:{}\nmin_time:{}\ncost_time:{}\ntimes:{}\n".format(alg_name,floder_name,n_gen,n_pop,curve,best_flags,min_time,cost_time,times)
    
    with open(result_file,"w") as f:
        f.write(content)


    data_json ={'algorithm':alg_name,'benchmark':floder_name,'generation':n_gen,'population':n_pop,'curve':curve,'best_flags':best_flags,'min_time':min_time,'cost_time':cost_time}
    result_file = "./result/json/{}_{}.json".format(alg_name,floder_name)
    with open(result_file,"w") as f:
        json.dump(data_json,f)




if __name__ == "__main__":
    # Use a small test set for verification
    testsuite = cbench+polybench # 示例
    # algorithm = ["NevergradAlg","GroupTunerAlg"] # 加入新算法名
    algorithm = ["CausalGuidedGA"]
    for alg in algorithm:
        for pro in testsuite:
            try:
                tqdm.write(f"Running {alg} on {pro}")
                # 这里的 select_flags 内部 eval(func) 会自动根据 alg 名找到 NevergradAlg 类
                select_flags(alg, pro, n_pop=10, n_gen=50) 
            except Exception as e:
                print(f"Error {alg} {pro}: {e}")
    