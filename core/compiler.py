# -*- coding: utf-8 -*-
import os
import subprocess
import shutil
import hashlib
from .utils import runcmd

class Compiler:
    def __init__(self, llvm_dir, tmp_dir):
        self.llvm_dir = llvm_dir
        self.tmp_dir = os.path.abspath(tmp_dir)
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.clang = os.path.join(llvm_dir, "clang")
        self.opt = os.path.join(llvm_dir, "opt")
        self.llc = os.path.join(llvm_dir, "llc")

    def source2IR(self, source, cflags, optlevel, output, cwd=None, instrument=False):
        if instrument:
            cmd = f'{self.clang} {cflags} -emit-llvm -c {optlevel} {source} -o {output}'
        else:
            cmd = f'{self.clang} {cflags} -emit-llvm -c {optlevel} -Xclang -disable-llvm-optzns {source} -o {output}'
        
        flag, ret = runcmd(cmd, cwd)
        if not flag:
            print(f"Error in source2IR: {cmd}\nOutput: {ret.stderr.decode() if ret else 'None'}")
        return flag

    def opt_ir(self, opt_params, IR, IR_opt, opt_stats, instrument=False, profdata=None, cwd=None):
        if instrument:
            cmd = f'{self.opt} -pgo-instr-gen -instrprof {IR} -o {IR_opt}'
            flag, ret = runcmd(cmd, cwd)
            return flag

        IR_input = IR
        if profdata and os.path.exists(profdata):
            IR_pgouse = IR + ".pgouse.bc"
            cmd = f'{self.opt} -pgo-instr-use --pgo-test-profile-file={profdata} {IR} -o {IR_pgouse}'
            flag, ret = runcmd(cmd, cwd)
            if flag:
                IR_input = IR_pgouse
            else:
                print(f"Warning: PGO use failed: {cmd}")

        cmd = f'{self.opt} -passes="{opt_params}" {IR_input} -o {IR_opt} -stats -stats-json 2> {opt_stats}'
        flag, ret = runcmd(cmd, cwd)
        
        if not flag:
            print(f"Error in opt: {cmd}\nOutput: {ret.stderr.decode() if ret else 'None'}")
            if os.path.exists(opt_stats):
                os.remove(opt_stats)
        
        return flag

    def IR2obj(self, IR_opt, obj, cwd=None):
        cmd = f'{self.llc} -O3 -filetype=obj -relocation-model=pic {IR_opt} -o {obj}'
        flag, ret = runcmd(cmd, cwd)
        if not flag:
            print(f"Error in IR2obj: {cmd}\nOutput: {ret.stderr.decode() if ret else 'None'}")
        return flag

    def compile_single_file(self, source, cflags, opt_params, output_obj, cwd=None):
        """
        完整编译流程：Source -> IR -> Opt IR -> Object
        返回: (success, stats_file_path)
        """
        if cwd is None:
            cwd = os.getcwd()
            
        fileroot = os.path.splitext(os.path.basename(source))[0]
        
        # Create unique temp dir for this compilation
        opt_hash = hashlib.md5(opt_params.encode('utf-8')).hexdigest()
        ir_dir = os.path.join(self.tmp_dir, fileroot, f'IR-{opt_hash}')
        os.makedirs(ir_dir, exist_ok=True)
        
        IR = os.path.join(ir_dir, fileroot + '.bc')
        IR_opt = os.path.join(ir_dir, fileroot + '.opt.bc')
        opt_stats = os.path.join(ir_dir, fileroot + '.opt_stats')
        
        # 1. Source -> IR
        if not self.source2IR(source, cflags, '-O3', IR, cwd=cwd):
            return False, None
            
        # 2. Opt IR
        if not self.opt_ir(opt_params, IR, IR_opt, opt_stats, cwd=cwd):
            return False, None
            
        # 3. IR -> Obj
        if not self.IR2obj(IR_opt, output_obj, cwd=cwd):
            return False, None
            
        return True, opt_stats
