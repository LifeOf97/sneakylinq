FROM python:3.11-alpine

ARG USER=dockeruser

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/${USER}

RUN addgroup -S ${USER} && adduser -S -G ${USER} ${USER}

USER ${USER}

WORKDIR ${HOME}/app

COPY --chown=${USER}:${USER} requirements.txt /

RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

COPY --chown=${USER}:${USER} . .

# ENTRYPOINT []