FROM debian:trixie-slim

ARG BUILD_DATE=unknown
ARG VERSION=unknown
ARG USER=hivemind
ARG ALPHA=true

ENV DEBIAN_FRONTEND noninteractive

SHELL ["/bin/bash", "-c"]

RUN apt-get update \
  && apt-get install -y --no-install-recommends git curl python3-dev python3-pip python3-venv vim python3-wheel g++ mpv build-essential libatomic1 alsa-utils libasound2-plugins flac libportaudio2 pulseaudio-utils pipewire pipewire-alsa mpg123 music123 sox swig\
  && c_rehash \
  && useradd --no-log-init $USER -m -c "HiveMind user" \
  && python3 -m venv /home/${USER}/.venv \
  && . /home/${USER}/.venv/bin/activate \
  && mkdir -p /home/${USER}/{.config,.cache,.local/share}/mycroft \
  && chown ${USER}:${USER} -R /home/${USER} \
  && apt-get --purge autoremove -y \
  && apt-get clean \
  && rm -rf ${HOME}/.cache /var/lib/apt /var/log/{apt,dpkg.log}

USER $USER

ENV IS_OVOS_CONTAINER "true"
ENV PATH /home/${USER}/.venv/bin:$PATH
ENV VIRTUAL_ENV /home/${USER}/.venv

COPY mycroft.conf.example /etc/mycroft/mycroft.conf
COPY --chown=${USER}:${USER} server.json.example /home/${USER}/.config/hivemind-core/server.json
COPY --chown=${USER}:${USER} ./docker_entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=${USER}:${USER} . /tmp/hivemind-player-protocol

RUN chmod +x /usr/local/bin/entrypoint.sh

RUN if [ "${ALPHA}" == "true" ]; then \
  pip3 --no-cache-dir install /tmp/hivemind-player-protocol[extras] hivemind-redis-database hivemind-http-protocol --pre; \
  else \
  pip3 --no-cache-dir install /tmp/hivemind-player-protocol[extras] hivemind-redis-database hivemind-http-protocol; \
  fi \
  && mkdir -p ${HOME}/.config/{hivemind,hivemind-core} ${HOME}/.local/{hivemind,share/hivemind} \
  && rm -rf /tmp/requirements.txt

ENTRYPOINT ["/bin/bash", "/usr/local/bin/entrypoint.sh"]

WORKDIR /home/${USER}
