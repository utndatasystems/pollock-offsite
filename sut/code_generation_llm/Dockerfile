FROM python:3.12-slim

WORKDIR /app
COPY ./sut/code_generation_llm/custom-bench.py ./
COPY ./sut/code_generation_llm/solution.py ./
COPY ./sut/code_generation_llm/requirements.txt ./
COPY ./sut/utils.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "custom-bench.py"]