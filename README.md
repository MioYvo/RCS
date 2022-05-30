# Risk Control System(RCS)
RCS is a risk control system for complete process, contains data-flow and customizable rules.

## Features
* Microservices.
* Full process for risk control. Defined rule and runer, receive data from api, clean and distribute data to rule engine, match rule and save punishment record.
* Customizable rules by simple and convenient http API.
* SceneScript, rule runner, simple use and wrote by Python for developers.

## Techs
* [RabbitMQ](https://www.rabbitmq.com/) for message queue.
* [fastapi](https://fastapi.tiangolo.com/) asynchronous http api.
* [odmantic](https://art049.github.io/odmantic/) asynchronous ODM for MongoDB.
* [aio-pika](https://aio-pika.readthedocs.io/en/latest/) asynchronous rabbitMQ support.


## Directory Structure
### Access
Event gateway. Pre-processing data.
### DataProcessor
Processing data flow, saving event data snapshot, calculate aggregate data, trigger rules.
### RuleEngine
Rule checking and building. Simple rule engine wrote by Python.
### SceneScript
Rule runner for Scene(pre-defined rules).



## Data flow
![Data flow](http://processon.com/chart_image/60d6daa67d9c087f547504b9.png)


## Deploy
1. MongoDB export/import
    > os CMD，not mongo Shell
   1. `mongodump --port 27017 -u "RCSAccess"  -p "c972745e8083bc5226e07f54f4d2b8ab71db3425ee2dac05811c162759628171" --authenticationDatabase "admin" --db RCSAccess --collection scene --archive=gz --gizp`
   2. `mongorestore --uri="mongodb://USERNAME:PASSWORD@HOST:PORT" --archive=backup.tgz`
2. MongoDB timezone is UTC，remember to convert it to local time（tool at `utils.gtz.Dt`）