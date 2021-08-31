# RCS Risk Control System 风险控制系统

## 项目结构
1. Access 事件网关，风控接入
2. DataProcessor 数据处理，保存事件快照，计算统计数据，触发规则
3. Deploy 部署相关

## Tips
1. MongoDB 导出导入
> 系统命令，不是mongo Shell 命令
   1. `mongodump --uri="mongodb://USERNAME:PASSWORD@HOST:PORT" --archive=backup.tgz`
   2. `mongorestore --uri="mongodb://USERNAME:PASSWORD@HOST:PORT" --archive=backup.tgz`