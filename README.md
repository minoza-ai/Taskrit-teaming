# Taskrit-teaming

티밍온 검색 엔진은 계정의 능력치를 벡터로 임베딩하여 저장하고, 사용자가 필요로 하는 작업에 따라 가장 유용한 팀원을 검색합니다.

- 계정(인간, AI, 로봇, 에셋)의 능력치 벡터화
- 사용자가 실행하길 원하는 태스크를 분해, 벡터 유사도로 검색
- 제약조건(평판, 단가, 가용성 등)에 따라 필터링
- 성공/실패, 작업 난이도 따라 ELO 레이팅으로 평판 관리

coding style follows @k-atusa/USAG-Lib

```bash
pip install sentence-transformers numpy
```
