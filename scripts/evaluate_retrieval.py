import pandas as pd
import os, sys
sys.path.append(os.getcwd())

import random
from sklearn.metrics import accuracy_score, classification_report
from app.rag.retriever import retrieve
from app.rag.vectorstore import get_collection

from dotenv import load_dotenv
load_dotenv()

def evaluate():
    print("开始执行检索模型评估 (模拟 7:3 划分)...")
    
    # 1. 读取数据
    if not os.path.exists("datasets/queries.csv"):
        print("找不到 datasets/queries.csv，请先生成数据")
        return

    df = pd.read_csv("datasets/queries.csv")
    data = list(zip(df["query"], df["faq_id"]))
    
    # 2. 模拟划分训练集/测试集 (7:3)
    random.seed(42)
    random.shuffle(data)
    split_idx = int(len(data) * 0.7)
    test_set = data[split_idx:]
    
    print(f"总数据量: {len(data)} | 测试集数量: {len(test_set)}")
    print("-" * 60)
    
    y_true = []
    y_pred = []
    
    # 3. 逐条测试
    correct = 0
    total = len(test_set)
    
    for q, true_id in test_set:
        # 检索 Top 1
        hits = retrieve(q, topk=1)
        pred_id = hits[0]['faq_id'] if hits else "None"
        
        y_true.append(true_id)
        y_pred.append(pred_id)
        
        if pred_id == true_id:
            correct += 1
            
    # 4. 输出指标
    acc = correct / total
    print(f"Top-1 准确率 (Accuracy): {acc:.2%}")
    if acc >= 0.85:
        print("结果达标 (>=85%)，证明预训练模型 BGE-Small 在本领域表现优异，无需微调。")
    else:
        print("准确率略低，建议后续通过微调优化。")
        
    print("-" * 60)
    print("混淆矩阵 (部分采样展示):")
    # 简单的文本展示
    print(f"{'Query (User Input)':<30} | {'True ID':<10} | {'Pred ID':<10} | {'Result'}")
    print("-" * 60)
    for i in range(min(10, len(test_set))):
        q, t = test_set[i]
        p = y_pred[i]
        res = "✅" if t == p else "❌"
        print(f"{q[:28]:<30} | {t:<10} | {p:<10} | {res}")

if __name__ == "__main__":
    # 确保向量库已加载
    get_collection() 
    evaluate()