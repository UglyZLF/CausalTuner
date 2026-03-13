#! /bin/bash
items="common optimizers params target warning joined separate undocumented c c++"
# items="optimizers"
for item in $items
do
	# gcc -Q -finline -fbranch-count-reg -fcombine-stack-adjustments -fcompare-elim -fcprop-registers -fdefer-pop -fdse -fforward-propagate -fguess-branch-probability -fif-conversion -fif-conversion2 -finline-functions-called-once -fipa-modref -fipa-profile -fipa-pure-const -fipa-reference -fipa-reference-addressable -fmerge-constants -fmove-loop-invariants -fomit-frame-pointer -freorder-blocks -fshrink-wrap -fsplit-wide-types -fssa-phiopt -ftoplevel-reorder -ftree-bit-ccp -ftree-builtin-call-dce -ftree-ccp -ftree-ch -ftree-coalesce-vars -ftree-copy-prop -ftree-dce -ftree-dominator-opts -ftree-dse -ftree-fre -ftree-pta -ftree-sink -ftree-slsr -ftree-sra -ftree-ter --help=$item >> /tmp/1
	gcc -Q -O0 --help=$item >> /tmp/t
	gcc -Q -O1 --help=$item >> /tmp/t
	gcc -Q -O2 --help=$item >> /tmp/t
	gcc -Q -O3 --help=$item >> /tmp/t
done

# cat /tmp/t

cat /tmp/t | grep "enabled" | awk '{print $1}'  | grep "\-f"| sort | uniq | xargs echo -n 
# cat /tmp/diff | grep "启用" | awk '{print $2'} | sort | uniq | xargs echo -n 
rm /tmp/t

