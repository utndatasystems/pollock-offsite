FROM python:3.12-slim

WORKDIR /app
COPY ./sut/llm_code_generator/custom-bench.py ./
COPY ./sut/llm_code_generator/solution.py ./
COPY ./sut/llm_code_generator/llm_utils.py ./
COPY ./sut/llm_code_generator/prompt.txt ./
COPY ./sut/llm_code_generator/requirements.txt ./
COPY ./sut/utils.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "custom-bench.py"]