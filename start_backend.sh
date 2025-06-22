#!/bin/bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
unset http_proxy https_proxy all_proxy
cd learn_mate_backend
make dev