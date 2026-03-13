# -*- coding: utf-8 -*-
import time
from copy import deepcopy
import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path
import fcntl
import argparse

# Add LLVMTuner to path
sys.path.append('/data/LLVMTuner-main/LLVMTuner-main')

parser = argparse.ArgumentParser()
parser.add_argument('--opt-cfg-json', help='')
parser.add_argument('--gen-ir', default=False, action='store_true', 
                    help='whether to only generate IR or to finish the whole compilation command')
parser.add_argument('--instrument-ir', default=False, action='store_true', 
                    help='whether to instrument in IR level for generating profdata')
parser.add_argument('--profdata', default='None', help='')
parser.add_argument('--optlevel', default='-O3', help='')
parser.add_argument('--llvm-dir', default='', help='')
args, unknown = parser.parse_known_args()


def create_file(output):
    # 获取文件锁
    with open(output, "w") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        # 检查文件是否已经存在
        script_content = '#!/bin/bash\necho "fake build!"\n'
        file.write(script_content)
        os.chmod(output, 0o755)
        # 释放文件锁
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)

class Clangopt:
    def __init__(self):
        '''
        初始化功能：（1）使用clang的-MJ命令生成compilation database；（2）从compilation database中获取编译信息
        '''
        if not args.opt_cfg_json:
            self.params=f'default<{args.optlevel[1:]}>'
            # Default tmp dir if not provided
            self.tmp_dir=os.path.join(os.path.expanduser('~/'), './tmp/')
        else:
            # 判断配置文件是否存在
            if not os.path.isfile(args.opt_cfg_json):
                print(f"Warning: config file {args.opt_cfg_json} not found. Using default params.")
                self.params=f'default<{args.optlevel[1:]}>'
                self.tmp_dir=os.path.join(os.path.expanduser('~/'), './tmp/')
            else:
                # 读取配置文件中的优化参数
                with open(args.opt_cfg_json, "r") as f:
                    cfg=json.load(f)
                self.params=cfg['params']
                self.tmp_dir=cfg['tmp_dir']
        
        os.makedirs(self.tmp_dir,exist_ok=True) 

        self.compiler='clang'
        
        # 使用clang的-MJ命令生成compilation database
        # maybe we could also use clang -###
        clang_cmd=[self.compiler]+unknown
        self.clang_cmd = clang_cmd
        print(' '.join(self.clang_cmd))
        
        optlevels=['-O3','-O2','-O1','-O0','-Oz','-O4','-Ofast','-Og','-Os']
        cmd=[x for x in clang_cmd if x not in optlevels ]
        cmd=' '.join(cmd)
        hash_str=hashlib.md5((cmd+str(self.params)).encode('utf-8')).hexdigest() 
        MJfile=os.path.join(self.tmp_dir, f'MJ-{hash_str}.json')
        cmd = cmd + ' -MJ {} ---xxx'.format(MJfile)
        ret = subprocess.run(cmd, shell=True, capture_output=True)
        
        self.objs=[]
        if '-c' in clang_cmd or '-S' in clang_cmd:
            self.link=False
        else:
            #意味着该命令形式为 clang *.c 或者 clang *.o
            self.link=True
        
        # 从compilation database中获取编译信息
        if os.path.isfile(MJfile):
            with open(MJfile,"r") as f:
                cdb = [json.loads(line[:-2]) for line in f]
            os.remove(MJfile)
            self.cdb=cdb
        # 如果该命令为链接obj文件生成二进制
        else:
            self.cdb = None
        
    
    def _single_compile(self, x):
        source=x['file']
        fileroot,fileext=os.path.splitext(source)
        fileroot = fileroot.replace('/','_')
        
        # Always use self.params, ignore hotfiles logic
        if isinstance(self.params, (str)):
            opt_str=self.params
        else:
            # If params is a dict (per-file config), try to look up, otherwise fallback
            if fileroot in self.params:
                opt_str=self.params[fileroot]
            else:
                 # Fallback or default
                opt_str=f'default<{args.optlevel[1:]}>'
        
        IR_dir=os.path.join(self.tmp_dir, fileroot, 'IR-{}/'.format( hashlib.md5(opt_str.encode('utf-8')).hexdigest()))
        os.makedirs(IR_dir, exist_ok=True)
        
        with open(os.path.join(IR_dir, 'seq.json'),'w') as ff:
            json.dump(opt_str, ff, indent=4)
        
        directory=x['directory']
        obj=x['output']
        
        self.objs.append(obj)
        
        IR=os.path.join(IR_dir, fileroot +'.bc')
        IR_pgouse=os.path.join(IR_dir, fileroot +'.pgouse.bc')
        IR_opt=os.path.join(IR_dir,fileroot+'.opt.bc')
        obj_cp = os.path.join(IR_dir,fileroot+'.o')
        
        asm=os.path.join(IR_dir, fileroot+'.s')
        opt_stats=os.path.join(IR_dir, fileroot+'.opt_stats')
        bfi=os.path.join(IR_dir, fileroot +'.bfi')
        cmd = deepcopy(self.clang_cmd)

        if '-o' in cmd:
            j=cmd.index('-o')
            del cmd[j:j+2]
        cmd=[x for x in cmd if x!='---xxx' and x!='-c' and x!='-S' and not x.endswith('.c') and not x.endswith('.cpp') and not x.endswith('.cc') and not x.endswith('.cxx') and not x.endswith('.C')]
        cflags = ' '.join(cmd[1:])
        
        if args.instrument_ir or not os.path.isfile(IR_opt):#
            self.source2IR(args.llvm_dir, source, cflags, args.optlevel, IR, cwd=directory)
            flag = self.opt(args.llvm_dir, opt_str, IR, IR_pgouse, IR_opt, opt_stats, bfi)
            assert flag
        
        if not args.gen_ir: #
            if not os.path.isfile(obj_cp):
                flag = self.IR2obj(args.llvm_dir, IR_opt, obj, obj_cp, cflags, cwd=directory)
                assert flag
            else:
                cp_cmd = f'cp {obj_cp} {obj}'
                ret = subprocess.run(cp_cmd, cwd=directory, shell=True, capture_output=True)
                assert ret.returncode == 0
        else:
            if not os.path.isfile(obj_cp):
                flag = self.IR2obj(args.llvm_dir, IR_opt, obj_cp, None, cflags, cwd=directory)
                assert flag

        return True
    
    def _compile(self):
        final_flag=True
        # 如果该命令为链接obj文件生成二进制
        if self.cdb == None:
            if args.instrument_ir:
                link_cmd = ' '.join(self.clang_cmd) + ' -fprofile-generate'
            else:
                link_cmd = ' '.join(self.clang_cmd)
            with open(os.path.join(self.tmp_dir, 'link_cmd.json'),'w') as ff:
                json.dump(link_cmd, ff, indent=4)

            if not args.gen_ir:#如果是正常build
                ret = subprocess.run(link_cmd, cwd =os.getcwd(), shell=True, capture_output=True)
                assert ret.returncode == 0, [os.getcwd(), link_cmd]
            else:#如果只是生成IR，而不是生成最终二进制
                if '-o' in self.clang_cmd:
                    j = self.clang_cmd.index('-o')
                    outputname = self.clang_cmd[j+1]
                else:
                    outputname = 'a.out'
                output = os.path.join(os.getcwd(), outputname)
                if not os.path.exists(output): #编译脚本中可能会对生成的binary做copy之类的操作，为避免报错，创建一个假文件
                    create_file(output)
                return
        
        else:
            # Iterate over all files, no hotfiles check
            for x in self.cdb:
                flag = self._single_compile(x)
                if not flag:
                    final_flag=False
                # 记录目标文件，在function_wrap中的所有编译完成后对其删除以保证下次仍然会重新编译
                # Note: hot_objs.json logic removed or simplified? 
                # Original code writes to hot_objs.json if hotfiles logic is used OR NOT used (in the else block).
                # The purpose is likely to track objects to be deleted for recompilation.
                # I will keep writing to hot_objs.json as 'objs.json' or just keep name to avoid breaking things?
                # Let's keep writing to hot_objs.json just in case.
                if not args.gen_ir:
                    obj_abspath = os.path.join(x['directory'], x['output'])
                    with open(os.path.join(self.tmp_dir, 'hot_objs.json'),'a') as ff:
                        ff.write(f"{obj_abspath}\n")
                # 改变源文件时间戳保证下次仍然会重新编译
                Path(x['file']).touch()
            
            
            if self.link:#如果命令为clang *.c -o a.out形式，既有编译为.o也有链接.o为目标文件的操作
                
                link_cmd_wo_objs = [aa for aa in self.clang_cmd if not aa.endswith('.c') and not aa.endswith('.cpp') and not aa.endswith('.cc') and not aa.endswith('.cxx')]
                link_cmd_wo_objs = ' '.join(link_cmd_wo_objs)
                
                if '-o' in self.clang_cmd:
                    j = self.clang_cmd.index('-o')
                    output = self.clang_cmd[j+1]
                else:
                    output = 'a.out'
                objs_str = ' '.join(self.objs)
                
                if args.instrument_ir:
                    link_cmd = f'{link_cmd_wo_objs} {objs_str} -fprofile-generate'
                else:
                    link_cmd = f'{link_cmd_wo_objs} {objs_str}'
                ret = subprocess.run(link_cmd, shell=True, capture_output=True)
                assert ret.returncode == 0, link_cmd
                with open(os.path.join(self.tmp_dir, 'link_cmd.json'),'w') as ff:
                    json.dump(link_cmd, ff, indent=4)
                
    

    @staticmethod
    def runcmd(cmd, cwd=None, timeout=None):
        '''
        用于执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
        这里接受的cmd是一个string, cwd是当前工作路径
        '''
        try:
            ret=subprocess.run(cmd, cwd=cwd, capture_output=True,shell=True,timeout=timeout)
            if ret.returncode == 0:
                flag=True
            else:
                flag=False
                # Print stderr if failed
                if ret.stderr:
                    print(ret.stderr.decode('utf-8', errors='ignore'))
        except Exception as e:
            print(f"Exception running command: {e}")
            flag=False
            ret=None
        return flag, ret
    
    
    @classmethod
    def source2IR(self, llvm_dir, source, cflags, optlevel, output, cwd=None):
        compiler_path = os.path.join(llvm_dir, self.compiler) if llvm_dir else self.compiler
        if args.instrument_ir:
            cmd = f'{compiler_path} {cflags} -emit-llvm -c {optlevel} {source} -o {output}'
        else:
            cmd = f'{compiler_path} {cflags} -emit-llvm -c {optlevel} -Xclang -disable-llvm-optzns {source} -o {output}'
        
        flag, ret = self.runcmd(cmd, cwd)
        assert flag == True, 'Check command in {}: {}'.format(cwd, cmd)
    
    
    @classmethod
    def opt(cls, llvm_dir, opt_params,  IR, IR_pgouse, IR_opt, opt_stats, bfi, cwd=None):            
        opt_bin = os.path.join(llvm_dir, "opt") if llvm_dir else "opt"
        
        if args.instrument_ir:
            cmd=f'{opt_bin} -pgo-instr-gen -instrprof {IR} -o {IR_opt}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, cmd
            return flag


        if args.profdata and args.profdata != 'None':
            cmd = f'{opt_bin} -pgo-instr-use --pgo-test-profile-file={args.profdata} {IR} -o {IR_pgouse}'
            flag, ret = cls.runcmd(cmd, cwd)
            assert flag == True, cmd
            
        else:
            IR_pgouse = IR
        
        cmd = f'{opt_bin} -passes="{opt_params}" {IR_pgouse} -o {IR_opt} -stats -stats-json 2> {opt_stats}'
        flag, ret = cls.runcmd(cmd, cwd)
        if not flag:
            print('wrong saved stats', opt_stats)
            if os.path.exists(opt_stats):
                os.remove(opt_stats)
        if os.path.exists(IR):
            os.remove(IR)
        assert flag == True, cmd
        return flag
    
    
    @classmethod
    def IR2obj(cls, llvm_dir, IR_opt, obj, obj_cp, cflags, cwd=None):
        llc_bin = os.path.join(llvm_dir, "llc") if llvm_dir else "llc"
        cmd = llc_bin +' -O3 -filetype=obj -relocation-model=pic {} -o {}'.format(IR_opt, obj)
        flag, ret = cls.runcmd(cmd, cwd)
        # print(cmd,cwd)
        assert flag == True, cmd
        
        if obj_cp != None:
            cp_cmd = f'cp {obj} {obj_cp}'
            ret = subprocess.run(cp_cmd, cwd=cwd, shell=True, capture_output=True)
            assert ret.returncode == 0
        
        return flag
    
    
    
def main():
    clangopt=Clangopt()
    clangopt._compile()

    
if __name__ == "__main__":   
    # print('command options:', unknown)
    clangopt=Clangopt()
    clangopt._compile()
