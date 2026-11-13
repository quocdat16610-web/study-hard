FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends qemu-system-x86 \
 && rm -rf /var/lib/apt/lists/* \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} +
USER 65534:65534
