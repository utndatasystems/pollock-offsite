FROM python:3.12-slim

WORKDIR /app
COPY ./sut/full_llm_loader/custom-bench.py ./
COPY ./sut/full_llm_loader/solution.py ./
COPY ./sut/full_llm_loader/llm_utils.py ./
COPY ./sut/full_llm_loader/llm_config.py ./
COPY ./sut/full_llm_loader/build_prompt_utils.py ./
COPY ./sut/full_llm_loader/prompts ./prompts
COPY ./sut/full_llm_loader/requirements.txt ./
COPY ./sut/utils.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "custom-bench.py"]
