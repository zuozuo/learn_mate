如果改了 learn_mate_backend 的代码，commit 代码之前执行 Bash(cd learn_mate_backend && ./before_commit.sh)
如果改了 learn_mate_frontent 的代码，commit 代码之前执行 Bash(cd learn_mate_frontend && pnpm lint && pnpm lint:fix && pnpm type-check && pnpm format && pnpm build)
