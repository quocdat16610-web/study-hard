KVER    ?= 6.6.8
VARIANT ?= minimal
TPL     ?= module-basic
PREFIX  ?= /opt/grader

images:
	docker build -t grader-cpp images/cpp
	docker build -t grader-qemu images/qemu
	docker build -t grader-app -f images/app/Dockerfile .

kernel:
	docker build -t grader-kbuild:$(KVER)-$(VARIANT) --build-arg KVER=$(KVER) --build-arg VARIANT=$(VARIANT) \
		-f images/kbuild/Dockerfile qemu/kernels
	c=$$(docker create grader-kbuild:$(KVER)-$(VARIANT)) && docker cp $$c:/out/. qemu/kernels/ && docker rm $$c

initramfs:
	qemu/tools/build_initramfs.sh base

install:
	install -d -m 0755 $(PREFIX)/qemu
	cp -a qemu/configs qemu/guest qemu/kernels qemu/initrds qemu/snapshots qemu/templates qemu/tools $(PREFIX)/qemu/
	cp -a labs $(PREFIX)/
	install -d -m 0700 -o $${GRADER_USER:-grader} /var/lib/grader/work
	install -d -m 0700 -o $${GRADER_USER:-grader} $(PREFIX)/qemu/runtimes $(PREFIX)/qemu/logs $(PREFIX)/qemu/snapshots
	chmod -R a-w $(PREFIX)/qemu/kernels $(PREFIX)/qemu/initrds $(PREFIX)/qemu/templates $(PREFIX)/qemu/configs
	install -m 0644 qemu/configs/grader.slice /etc/systemd/system/grader.slice && systemctl daemon-reload

snapshot:
	python3 -m grader.sandbox.qemu snapshot $(TPL)

test:
	python3 -m pytest -q tests

.PHONY: images kernel initramfs install snapshot test
