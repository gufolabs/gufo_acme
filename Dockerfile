FROM python:3.12-slim-bullseye AS dev
COPY . /workspaces/gufo_acme
WORKDIR /workspaces/gufo_acme
RUN \
    set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends git\
    && pip install --upgrade pip\
    && pip install --upgrade build\
    && pip install -e .[test,lint,docs,ipython]
