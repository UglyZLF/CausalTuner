# -*- coding: utf-8 -*-

# === 原始映射定义 (确保位索引与 Pass 严格对应) ===
SEQS_GLOBAL = [['-sroa', '-jump-threading'], ['-mem2reg', '-gvn', '-instcombine'], ['-mem2reg', '-gvn', '-prune-eh'], ['-mem2reg', '-gvn', '-dse'], ['-mem2reg', '-loop-sink', '-loop-distribute'], ['-early-cse-memssa', '-instcombine'], ['-early-cse-memssa', '-dse'], ['-lcssa', '-loop-unroll'], ['-licm', '-gvn', '-instcombine'], ['-licm', '-gvn', '-prune-eh'], ['-licm', '-gvn', '-dse'], ['-memcpyopt', '-loop-distribute']]
FLAGS_GLOBAL = ['-tti', '-tbaa', '-scoped-noalias-aa', '-assumption-cache-tracker', '-targetlibinfo', '-verify', '-lower-expect', '-simplifycfg', '-domtree', '-sroa']

SEQS_G1 = [['-early-cse-memssa', '-instcombine'], ['-elim-avail-extern', '-early-cse-memssa', '-instcombine'], ['-gvn', '-instcombine'], ['-loop-sink', '--mem2reg']]
FLAGS_G1 = ['-sroa','-mem2reg','-gvn','-licm','-early-cse-memssa','-instcombine','-early-cse','-jump-threading','-globalopt','-loop-rotate']

SEQS_G2 = [['--mem2reg', '-simplifycfg', '-sroa', '-loop-unroll'], ['-constmerge', '-lcssa'], ['-early-cse', '-simplifycfg', '-sroa', '-loop-unroll'], ['-early-cse-memssa', '-instcombine'], ['-gvn', '-instcombine'], ['-licm', '-simplifycfg', '-sroa', '-loop-unroll'], ['-loop-rotate', '-callsite-splitting'], ['-simplifycfg', '-sroa', '-loop-unroll'], ['-sroa', '-loop-unroll']]
FLAGS_G2 = ['-mem2reg','-sroa','-licm','-gvn','-early-cse-memssa','-instcombine','-loop-rotate','-simplifycfg','-transform-warning','-sccp']

G1_LABELS = ['SEQ_G1_0', 'SEQ_G1_1', 'SEQ_G1_2', 'SEQ_G1_3', 'FLAG_G1_0', 'FLAG_G1_1', 'FLAG_G1_2', 'FLAG_G1_3', 'FLAG_G1_4', 'FLAG_G1_5', 'FLAG_G1_6', 'FLAG_G1_7', 'FLAG_G1_8', 'FLAG_G1_9']
GLOBAL_LABELS = ['SEQ_GLOB_0', 'SEQ_GLOB_1', 'SEQ_GLOB_2', 'SEQ_GLOB_3', 'SEQ_GLOB_4', 'SEQ_GLOB_5', 'SEQ_GLOB_6', 'SEQ_GLOB_7', 'SEQ_GLOB_8', 'SEQ_GLOB_9', 'SEQ_GLOB_10', 'SEQ_GLOB_11', 'FLAG_GLOB_0', 'FLAG_GLOB_1', 'FLAG_GLOB_2', 'FLAG_GLOB_3', 'FLAG_GLOB_4', 'FLAG_GLOB_5', 'FLAG_GLOB_6', 'FLAG_GLOB_7', 'FLAG_GLOB_8', 'FLAG_GLOB_9']

G1_TIER1_INDICES = []
G2_TIER1_INDICES = [6, 19, 7, 18, 15]

G1_GUIDANCE_NODES = []
G2_GUIDANCE_NODES = [
    {
        "index": 7,
        "conditions": [
            {
                "feature": "instcount.NumAddInst",
                "direction": ">",
                "threshold": 0.0462,
                "global_avg": 0.038562
            },
            {
                "feature": "instcount.NumPHIInst",
                "direction": "<",
                "threshold": 0.001578,
                "global_avg": 0.002551
            },
            {
                "feature": "instcount.NumStoreInst",
                "direction": ">",
                "threshold": 0.147266,
                "global_avg": 0.138015
            }
        ]
    },
    {
        "index": 20,
        "conditions": [
            {
                "feature": "instcount.NumAddInst",
                "direction": "<",
                "threshold": 0.03003,
                "global_avg": 0.038562
            },
            {
                "feature": "instcount.NumLoadInst",
                "direction": "<",
                "threshold": 0.31047,
                "global_avg": 0.318962
            }
        ]
    },
    {
        "index": 9,
        "conditions": [
            {
                "feature": "instcount.NumSubInst",
                "direction": ">",
                "threshold": 0.018809,
                "global_avg": 0.016891
            }
        ]
    },
    {
        "index": 15,
        "conditions": [
            {
                "feature": "instcount.NumAddInst",
                "direction": ">",
                "threshold": 0.045165,
                "global_avg": 0.038562
            },
            {
                "feature": "instcount.NumLoadInst",
                "direction": ">",
                "threshold": 0.331762,
                "global_avg": 0.318962
            },
            {
                "feature": "instcount.NumAllocaInst",
                "direction": "<",
                "threshold": 0.036945,
                "global_avg": 0.045166
            }
        ]
    },
    {
        "index": 17,
        "conditions": [
            {
                "feature": "instcount.NumStoreInst",
                "direction": ">",
                "threshold": 0.148349,
                "global_avg": 0.138015
            }
        ]
    },
    {
        "index": 12,
        "conditions": [
            {
                "feature": "instcount.NumBrInst",
                "direction": ">",
                "threshold": 0.116997,
                "global_avg": 0.096938
            },
            {
                "feature": "instcount.NumStoreInst",
                "direction": ">",
                "threshold": 0.14444,
                "global_avg": 0.138015
            }
        ]
    },
    {
        "index": 4,
        "conditions": [
            {
                "feature": "instcount.NumPHIInst",
                "direction": ">",
                "threshold": 0.003749,
                "global_avg": 0.002551
            }
        ]
    },
    {
        "index": 10,
        "conditions": [
            {
                "feature": "instcount.NumCallInst",
                "direction": "<",
                "threshold": 0.025292,
                "global_avg": 0.031246
            }
        ]
    },
    {
        "index": 18,
        "conditions": [
            {
                "feature": "loop.MaxLoopDepth",
                "direction": ">",
                "threshold": 3.239077,
                "global_avg": 3.0
            },
            {
                "feature": "instcount.NumCallInst",
                "direction": "<",
                "threshold": 0.0258,
                "global_avg": 0.031246
            }
        ]
    },
    {
        "index": 16,
        "conditions": [
            {
                "feature": "instcount.NumAllocaInst",
                "direction": "<",
                "threshold": 0.044238,
                "global_avg": 0.045166
            }
        ]
    },
    {
        "index": 21,
        "conditions": [
            {
                "feature": "instcount.NumBitCastInst",
                "direction": ">",
                "threshold": 0.008837,
                "global_avg": 0.007603
            },
            {
                "feature": "instcount.NumSubInst",
                "direction": "<",
                "threshold": 0.014845,
                "global_avg": 0.016891
            },
            {
                "feature": "instcount.NumAllocaInst",
                "direction": ">",
                "threshold": 0.051876,
                "global_avg": 0.045166
            }
        ]
    },
    {
        "index": 11,
        "conditions": [
            {
                "feature": "instcount.NumSubInst",
                "direction": "<",
                "threshold": 0.012206,
                "global_avg": 0.016891
            },
            {
                "feature": "loop.NestedRatio",
                "direction": "<",
                "threshold": 0.273326,
                "global_avg": 0.312621
            }
        ]
    },
    {
        "index": 0,
        "conditions": [
            {
                "feature": "instcount.NumStoreInst",
                "direction": "<",
                "threshold": 0.130414,
                "global_avg": 0.138015
            }
        ]
    },
    {
        "index": 6,
        "conditions": [
            {
                "feature": "instcount.NumMulInst",
                "direction": "<",
                "threshold": 0.003659,
                "global_avg": 0.009704
            }
        ]
    },
    {
        "index": 13,
        "conditions": [
            {
                "feature": "instcount.NumCallInst",
                "direction": ">",
                "threshold": 0.04181,
                "global_avg": 0.031246
            }
        ]
    },
    {
        "index": 1,
        "conditions": [
            {
                "feature": "instcount.NumCallInst",
                "direction": ">",
                "threshold": 0.049883,
                "global_avg": 0.031246
            },
            {
                "feature": "instcount.NumAllocaInst",
                "direction": ">",
                "threshold": 0.059316,
                "global_avg": 0.045166
            }
        ]
    },
    {
        "index": 2,
        "conditions": [
            {
                "feature": "instcount.NumBrInst",
                "direction": "<",
                "threshold": 0.094951,
                "global_avg": 0.096938
            }
        ]
    },
    {
        "index": 14,
        "conditions": [
            {
                "feature": "instcount.NumICmpInst",
                "direction": "<",
                "threshold": 0.033786,
                "global_avg": 0.038901
            }
        ]
    }
]


def get_search_tier_indices(group_id, prog_features):
    """返回分层索引：Tier1(因果核), Tier2(特征激活), Tier3(残差)"""
    if group_id == 1:
        total_range, tier1, guidance = list(range(14)), G1_TIER1_INDICES, G1_GUIDANCE_NODES
    else:
        total_range, tier1, guidance = list(range(22)), G2_TIER1_INDICES, G2_GUIDANCE_NODES
        
    tier2 = []
    for node in guidance:
        match = 0
        for r in node['conditions']:
            val = prog_features.get(r['feature'], 0)
            if (r['direction'] == ">" and val >= r['threshold']) or (r['direction'] == "<" and val <= r['threshold']):
                match += 1
        if len(node['conditions']) > 0 and (match / len(node['conditions']) >= 0.5):
            if node['index'] not in tier1: tier2.append(node['index'])
                
    active = set(tier1 + tier2)
    return tier1, tier2, [i for i in total_range if i not in active]

def decode_to_passes(group_id, bitstring):
    """将二进制列表 [1, 0, 1...] 转换为真实的 LLVM Pass 列表"""
    final_passes = []
    if group_id == 1:
        seqs, flags = SEQS_G1, FLAGS_G1
        split_idx = 4
    else:
        seqs, flags = SEQS_GLOBAL, FLAGS_GLOBAL
        split_idx = 12
        
    for i, val in enumerate(bitstring):
        if val == 1:
            if i < split_idx:
                final_passes.extend(seqs[i])
            else:
                final_passes.append(flags[i - split_idx])
    return final_passes
