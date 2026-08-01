FROM python:3.12-slim

WORKDIR /app
COPY ./sut/llm_hybrid_parser/llm-hybrid-bench.py ./
COPY ./sut/llm_hybrid_parser/solution.py ./
COPY ./sut/llm_hybrid_parser/llm.py ./
COPY ./sut/llm_hybrid_parser/dialect.py ./
COPY ./sut/llm_hybrid_parser/loader.py ./
COPY ./sut/llm_hybrid_parser/requirements.txt ./
COPY ./sut/utils.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "llm-hybrid-bench.py"]
