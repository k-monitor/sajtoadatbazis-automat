ARG UBUNTU_VERSION=22.04

FROM ubuntu:$UBUNTU_VERSION as build

RUN apt-get update && \
    apt-get install -y build-essential git

WORKDIR /app

RUN git clone https://github.com/ggerganov/llama.cpp .

RUN make server

FROM ubuntu:$UBUNTU_VERSION as runtime

COPY --from=build /app/server /server
RUN apt-get update && \
    apt-get install -y wget

EXPOSE 8000

ENV LC_ALL=C.utf8

ENTRYPOINT wget -nc -O ${MODEL_FILE} ${MODEL_URL} ; /server -m ${MODEL_FILE} --port 8000 --host 0.0.0.0
