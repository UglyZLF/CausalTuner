import os
import joblib
import numpy as np
import sys

# 路径处理，确保能导入同目录下的 features
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from features import get_bench_raw_features

class ProgClassifier:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(__file__), 'prog_classifier.joblib')
        if os.path.exists(model_path):
            data = joblib.load(model_path)
            self.model = data['model']
            self.feature_cols = data['feature_cols']
        else:
            self.model = None
            print("Warning: Classifier model not found. Use fallback logic.")

    def predict_group(self, bench_name):
        """
        输入程序名，返回 1 或 2
        """
        # 1. 提取特征
        features_dict = get_bench_raw_features(bench_name)
        
        if features_dict is None:
            print(f"Warning: Could not get features for {bench_name}, fallback to Group 2")
            return 2
        
        # 2. 转换为模型输入向量
        if self.model:
            input_vector = [features_dict.get(c, 0) for c in self.feature_cols]
            prediction = self.model.predict([input_vector])[0]
            return int(prediction)
        else:
            # 如果模型没训练好，使用硬编码兜底 (针对已知程序)
            from train_classifier import GROUP1_PROGS
            return 1 if bench_name in GROUP1_PROGS else 2

# 创建单例对象供外部直接调用
classifier_instance = ProgClassifier()

def get_prog_group(bench_name):
    return classifier_instance.predict_group(bench_name)