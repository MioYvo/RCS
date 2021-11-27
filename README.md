<<<<<<< HEAD
# RCS风控系统（PY）
=======
# RCS Risk Control System 风险控制系统

## 项目结构
1. Access 事件网关，风控接入
2. DataProcessor 数据处理，保存事件快照，计算统计数据，触发规则
3. Deploy 部署相关

## Tips
1. MongoDB 导出导入
    > 系统命令，不是mongo Shell 命令
   1. `mongodump --port 27017 -u "RCSAccess"  -p "c972745e8083bc5226e07f54f4d2b8ab71db3425ee2dac05811c162759628171" --authenticationDatabase "admin" --db RCSAccess --collection scene --archive=gz --gizp`
   2. `mongorestore --uri="mongodb://USERNAME:PASSWORD@HOST:PORT" --archive=backup.tgz`
2. MongoDB 数据存储的时区（timezone）是UTC，所以使用时记得转换（工具`utils.gtz.Dt`）
>>>>>>> 7891de4f4b76cbb7f6457534b2df47dfcf22b035
