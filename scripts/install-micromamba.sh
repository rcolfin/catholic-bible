#!/usr/bin/env bash

# Installs micromamba

set -euo pipefail

function log() {
    >&2 echo "$(date '+%Y-%m-%d %H:%M:%S') ${*}"
}

function fail() {
    log ERROR "$@"
    return 1
}

function get_mamba_exe() {
    local SCRIPT

    if [ -n "${MAMBA_EXE+x}" ] && [ -f "${MAMBA_EXE}" ]; then
        echo "${MAMBA_EXE}"
        return
    fi

    SCRIPT=$(cat <<EOF
if [ -f ~/.bash_profile ]; then
    source ~/.bash_profile >/dev/null 2>&1
elif [ -f ~/.bashrc ]; then
    source ~/.bashrc >/dev/null 2>&1
fi
exec echo "\$MAMBA_EXE"
EOF
)

    exec /bin/bash --init-file <(echo "$SCRIPT")
}

function get_mamba_root_prefix() {
    local SCRIPT

    if [ -n "${MAMBA_ROOT_PREFIX+x}" ] && [ -d "${MAMBA_ROOT_PREFIX}" ]; then
        echo "${MAMBA_ROOT_PREFIX}"
        return
    fi

    SCRIPT=$(cat <<EOF
if [ -f ~/.bash_profile ]; then
    source ~/.bash_profile >/dev/null 2>&1
elif [ -f ~/.bashrc ]; then
    source ~/.bashrc >/dev/null 2>&1
fi
exec echo "\$MAMBA_ROOT_PREFIX"
EOF
)

    exec /bin/bash --init-file <(echo "$SCRIPT")
}

function main() {
    local MAMBA_EXE
    local MAMBA_ROOT_PREFIX

    MAMBA_EXE=$(get_mamba_exe)
    MAMBA_ROOT_PREFIX=$(get_mamba_root_prefix)

    if [ -n "${MAMBA_EXE+x}" ] && [ -f "${MAMBA_EXE}" ] && [ -n "${MAMBA_ROOT_PREFIX:+x}" ] && [ -d "${MAMBA_ROOT_PREFIX}" ]; then
        log INFO "micromamba already exists."
        log INFO "Run eval \"\$(${MAMBA_EXE} shell hook --shell bash)\""
        return 0
    fi

    log INFO "installing micromamba"

    true | "${SHELL}" <(curl -sL micro.mamba.pm/install.sh) || { fail "Failed to install micromamba."; return 1; }

    MAMBA_EXE=$(get_mamba_exe)
    MAMBA_ROOT_PREFIX=$(get_mamba_root_prefix)
    if [ -z "${MAMBA_EXE+x}" ] || [ ! -f "${MAMBA_EXE}" ]; then
        fail "No mamba executable found.";
        return 1
    fi

    export MAMBA_ROOT_PREFIX
    log INFO "micromamba self-update"

    "${MAMBA_EXE}" self-update -q || { fail "Failed to update micromamba."; return 1; }
}

main
