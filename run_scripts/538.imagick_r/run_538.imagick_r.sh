#!/bin/bash

./imagick_r_base.none -limit disk 0 train_input.tga -resize 320x240 -shear 31 -edge 140 -negate -flop -resize 900x900 -edge 10 train_output.tga 0<&- > train_convert.out 2>> train_convert.err
