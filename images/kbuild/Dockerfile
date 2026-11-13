# Builds the guest kernel AND is the image student modules are compiled in (identical vermagic).
# build context: qemu/kernels
FROM ubuntu:24.04
ARG KVER=6.6.8
ARG VARIANT=minimal
ARG KSRC=https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KVER}.tar.xz
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential bc bison flex libelf-dev libssl-dev xz-utils curl ca-certificates kmod \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /usr/src/linux
RUN curl -fsSL "$KSRC" | tar -xJ --strip-components=1
COPY config-${KVER}-minimal config-${KVER}-${VARIANT} /tmp/cfg/
RUN cat /tmp/cfg/* | grep '^CONFIG_' | sort -u > /tmp/frag \
 && make KCONFIG_ALLCONFIG=/tmp/frag allnoconfig \
 && while read -r s; do grep -qxF "$s" .config || { echo "config not applied: $s" >&2; exit 1; }; done < /tmp/frag \
 && make -j"$(nproc)" bzImage modules \
 && install -D arch/x86/boot/bzImage /out/vmlinuz-${KVER}-${VARIANT} \
 && cp Module.symvers /tmp/ && make clean && mv /tmp/Module.symvers . \
 && chmod -R a+rX,go-w /usr/src/linux
USER 65534:65534
WORKDIR /work
