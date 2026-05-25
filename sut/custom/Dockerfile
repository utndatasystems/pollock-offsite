FROM python:3.12-slim

WORKDIR /app
COPY ./sut/custom/custom-bench.py ./
COPY ./sut/custom/solution.py ./
COPY ./sut/custom/requirements.txt ./
COPY ./sut/utils.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "custom-bench.py"]