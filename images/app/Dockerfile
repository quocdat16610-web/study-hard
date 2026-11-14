# API and worker share one image. The worker drives the host Docker daemon through the mounted socket.
# build context: repository root
FROM python:3.12-slim
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
WORKDIR /app
COPY pyproject.toml ./
COPY grader ./grader
RUN pip install --no-cache-dir . && useradd -r -u 10001 grader
USER 10001
