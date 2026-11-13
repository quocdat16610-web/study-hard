# Toolchain + runtime for user-space labs and toy-kernel builds. Runs under gVisor, never as root.
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      clang-18 clang-tidy-18 lld-18 llvm-18 libclang-rt-18-dev cppcheck \
 && rm -rf /var/lib/apt/lists/* \
 && for t in clang clang++ clang-tidy ld.lld llvm-symbolizer llvm-objdump; do ln -s /usr/bin/$t-18 /usr/local/bin/$t; done \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} +
ENV ASAN_OPTIONS=detect_leaks=1:abort_on_error=0:halt_on_error=1:symbolize=1 \
    UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
    ASAN_SYMBOLIZER_PATH=/usr/local/bin/llvm-symbolizer \
    HOME=/tmp TMPDIR=/tmp
USER 65534:65534
WORKDIR /work
