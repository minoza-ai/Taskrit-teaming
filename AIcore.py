import re
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 계정의 적혀있는 능력치를 단일 항목으로 분해
def SplitAbilities(text):
    abilities = [item.strip() for item in text.split(',') if item.strip()]
    return abilities

# 태스크를 단일 항목으로 분해 !!! API 써서 생략된 하위 항목 더해야 함 !!!
def SplitTasks(text):
    pattern = r',|\s+그리고\s+|\s+하고\s+|\s+하며\s+|\s+랑\s+|\s+및\s+'
    raw_tasks = re.split(pattern, text)
    tasks = [t.strip() for t in raw_tasks if len(t.strip()) > 1]
    if not tasks: # return itself if not splitable
        tasks = [text]
    return tasks

# 문장 의미 벡터화
def SentenceEmbedding(text):
    return model.encode(text).tolist()

# 벡터간 코사인 유사도 계산
def CosineSimilarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
