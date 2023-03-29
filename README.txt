This demo shows how to get data from exchangerate.host for base currency = BTC and write it to Clickhouse using Airflow.
Data loading is scheduled for every 3 hours.
Historical data can be also reloaded.
Execute docker-compose up to launch containers with Airflow (Local executor) and Clickhouse.
In the initsql\init_database.sql there is an init script for Clickhouse.
.env file has Clickhouse user/password (that stuff shoudn't be stored in Git and here is just for demo reason).
dags\click.py contains a DAG with two tasks: one is for getting data from API and writing it to the staging layer, another one is for transferring data to a datamart layer using Switch partition technique.
dags\scripts\clicksql.py contains Clickhouse SQL scripts for processing data.

TODO:
- Shutdown clickhouse-init container after executing the initial script.
- Write details about the solution and each task in the DAG.


