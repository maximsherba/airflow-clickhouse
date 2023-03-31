from datetime import datetime, timedelta
import logging
import os
from typing import Dict, Any
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import json

import scripts.clicksql as clicksql

LOAD_START_DATE = datetime(2023, 3, 20)
base_cur = "BTC"
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "execution_timeout": timedelta(minutes=90),
    "retries": 2,
    "retry_delay": timedelta(seconds=10),
}

def extract_from_API(date: str = "latest") -> Dict[str,float]:    
    import requests

    params = {
        "base": base_cur
        #"symbols": "USD"
    }  
    url = f"https://api.exchangerate.host/{date}"
    logging.info(f"url {url}")
    try:
        response = requests.get(url,params=params)
    except Exception as e:
        logging.error(f"API extraction failed with exception {e}")
    if response != None and response.status_code == 200:        
        data = response.json()["rates"]
        logging.info(f"data {data}")
    else:
        logging.error(f"Unable to get data for {url}")
        raise Exception("API extraction failed with status code {response.status_code}")
    return list(data.items())

def get_connection() -> Any:
    from clickhouse_driver import Client

    logging.info("Getting connection parameters and making a clickhouse connection")
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
    CLICKHOUSE_PORT = os.getenv("CLICKHOUSE_PORT")
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
    CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")   
    return Client(host=CLICKHOUSE_HOST, 
                  port=CLICKHOUSE_PORT, 
                  user=CLICKHOUSE_USER, 
                  password=CLICKHOUSE_PASSWORD,
                  database=CLICKHOUSE_DB) 

def query_clickhouse(query: str) -> Any:
    logging.info(f"Executing a query in clickhouse {query}")
    client = get_connection()
    try:
        result = client.execute(query)
    except Exception as e:
        logging.error(f"Unable to execute query {query} with the error {e}")
        raise Exception(f"Error executing query {query}")
    return result

def API_to_click(**context:  Dict[str, Any]) -> None:    
    data_start = context["data_interval_start"].strftime("%Y-%m-%d")
    if data_start == datetime.now().strftime("%Y-%m-%d"):
        data = extract_from_API()
    else:
        data = extract_from_API(data_start)
    #There is a problem with multi querying clickhouse which I haven't solved, 
    # therefore here we send each query separately
    query_clickhouse(clicksql.DDL_BRONZE_DAILY_EXCHANGE_RATES_DROP)
    query_clickhouse(clicksql.DDL_DAILY_EXCHANGE_RATES_CREATE.format(stage='bronze'))
    query_clickhouse(clicksql.DDL_BRONZE_DAILY_EXCHANGE_RATES_INSERT.format(base=base_cur,
                                                                            date=data_start,
                                                                            data=data))
    
def click_bronze_to_gold(**context:  Dict[str, Any]) -> None:
    data_start = context["data_interval_start"].strftime("%Y-%m-%d")
    query_clickhouse(clicksql.DDL_DAILY_EXCHANGE_RATES_CREATE.format(stage='gold'))
    query_clickhouse(clicksql.DDL_GOLD_DAILY_EXCHANGE_RATES_EXCHANGE.format(date=data_start.replace("-","")))


with DAG(
    dag_id="exchange_rates_to_click",
    start_date=LOAD_START_DATE,
    schedule_interval=timedelta(hours=3),
    max_active_runs=1,
    default_args=default_args,
) as dag:
    
    extractAPI = PythonOperator(
        task_id="extractAPI", 
        python_callable=API_to_click,
        wait_for_downstream=True,
        )

    click = PythonOperator(
        task_id="click_bronze_to_gold", 
        python_callable=click_bronze_to_gold,
        wait_for_downstream=True,
        )

    extractAPI >> click

