#!/bin/bash
# Sourced by the musl userland builders.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="$(bash "$PROJECT_ROOT/build/current-platform.sh")"
MUSL_DIR="$PROJECT_ROOT/toolchain/${PLATFORM}-rux-linux-musl"
case "$PLATFORM" in
    riscv64)
        CC=riscv64-linux-gnu-gcc
        HOST=riscv64-linux-gnu
        ARCH_CFLAGS="-march=rv64gc_zicsr"
        SYSTEM_INCLUDE=/usr/riscv64-linux-gnu/include
        ;;
    x86_64)
        CC=x86_64-linux-gnu-gcc
        HOST=x86_64-linux-musl
        ARCH_CFLAGS=""
        SYSTEM_INCLUDE=/usr/include/x86_64-linux-gnu
        ;;
    *)
        echo "Minimal rootfs is not supported for PLATFORM=$PLATFORM" >&2
        return 1
        ;;
esac
export CC
MUSL_CFLAGS="-static $ARCH_CFLAGS -nostdinc -fno-stack-protector -isystem $MUSL_DIR/include -isystem $SYSTEM_INCLUDE -isystem /usr/include"
