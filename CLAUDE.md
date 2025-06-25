
## workflow 

* 每次都先归档 docs/latest_user_requirements.md 的内容 到 docs/user_requirements_history.md，用 append 的方式
* Always summary user requirements and generate todos, then overwrite docs/latest_user_requirements.md
* 如果改了 learn_mate_backend 的代码，commit 代码之前执行 Bash(cd /Users/zuozuo/workspace/projects/learn_mate/learn_mate_backend && ./before_commit.sh)
* 如果改了 learn_mate_frontent 的代码，commit 代码之前执行 Bash(cd /Users/zuozuo/workspace/projects/learn_mate/learn_mate_frontend && ./before_commit.sh)

## Rules:

* 不需要通过python 脚本来测试模拟前端的行为，没有意义
* 请记住你只需要确保  before_commit.sh 成功就行，不需要你实际启动服务器测试，这部分我会来手动完成                                                   
* 永远不要通过注释掉代码或者测试的方式来让测试通过，必须要找到导致测试失败的根本原因并解决它
