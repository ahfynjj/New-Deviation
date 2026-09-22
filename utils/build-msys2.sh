#!/usr/bin/env bash
# Project-local MSYS2 build entry. Called by build-msys2.ps1.
set -euo pipefail
export PATH=/usr/bin

target=${1:?target required}
tools=$(cygpath -u "${2:?tools directory required}")
native=$(cygpath -u "${3:?native compiler directory required}")
rebuild=${4:-0}
arm=$(cygpath -u "${5:?Arm compiler directory required}")
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
export PATH="$root/utils/host-tools:/usr/bin"
export PYTHONPATH="$tools/python-packages${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p local/logs
log="local/logs/${target}.log"
flags=(-j4)
if [[ "$rebuild" == 1 ]]; then
    flags+=(-B)
fi

run_target() {
    case "$target" in
        test)
            make -C src "${flags[@]}" test
            (cd src && timeout 60 ./test.elf)
            ;;
        runner)
            python3 -m unittest discover -s utils/tests -p 'test_*.py'
            ;;
        devo8)
            export PATH="$arm/bin:$PATH"
            # Arm GCC 8 canonicalizes some project header paths using the Windows
            # code page. In a non-ASCII checkout, discard only generated deps and
            # force compilation; never reuse objects without valid dependencies.
            if [[ "$root" == *[![:ascii:]]* ]]; then
                echo "Non-ASCII checkout: forcing full DEVO8 rebuild (GCC 8 dependency limitation)."
                for depdir in src/objs/devo8 src/libopencm3/lib/stm32/f1; do
                    if [[ -d "$depdir" ]]; then
                        find "$depdir" -maxdepth 1 -type f \( -name '*.P' -o -name '*.d' \) -delete
                    fi
                done
                flags+=(-B)
            fi
            # The pinned libopencm3's whitespace expression produces a trailing
            # backslash under Make 4.4; override the result without modifying it.
            make -C src "${flags[@]}" devo8 SRCLIBDIR="$root/src/libopencm3/lib"
            ;;
        emu_devo8|emu_tx15)
            export PATH="$native/bin:$PATH"
            make -C src "${flags[@]}" "win_$target" \
                FLTK_DIR="$native" PORTAUDIO_DIR="$native" \
                EXTRA_CFLAGS="-isystem $native/include"
            ;;
        lint)
            (cd src && python3 ../utils/run_linter.py --diff --skip-github)
            ;;
        *)
            echo "Unsupported target: $target" >&2
            return 2
            ;;
    esac
}

run_target 2>&1 | tee "$log"
