from datetime import datetime, timedelta
import json
import os
import requests
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

import os

dag_directory = os.path.dirname(os.path.abspath(__file__))

json_file_path = os.path.join(dag_directory, "jsonData/preferences.json")


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 2, 1),
    'email': 'amukayoung@gmail.com',
    'catchup':False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def load_data():
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def extract_data(**kwargs):
    ti = kwargs['ti']
    data = ti.xcom_pull(task_ids='load_data_task')

    deviceSet = set()
    deviceList = []

    for item in data:
        device_id = item.get("deviceId")
        app_version = item.get("appVersion", "STD001")
        device_model = item.get("deviceModel")
        os = item.get("os")
        os_version = item.get("osVersion")

        if device_id not in deviceSet:
            deviceDetail = {
                'id': device_id,
                'appversion': app_version,
                'devicemodel': device_model,
                'os': os,
                'osversion': os_version,
            }

            deviceSet.add(device_id)
            deviceList.append(deviceDetail)

    ti.xcom_push(key='deviceList', value=deviceList)

    return deviceList

def make_post_request(**kwargs):
    ti = kwargs['ti']
    deviceList = ti.xcom_pull(task_ids='extract_data_task', key='deviceList')

    api_endpoint = "http://localhost:8000/device_airflow/"

    headers = {
        'Content-Type': 'application/json', 
        'Accept':'application/json',
        'Content-Length':'<calculated when request is sent>',
        'Host':'<calculated when request is sent>',
        # 'User-Agent':'PostmanRuntime/7.36.1',
        'Accept':'*/*',
        'Accept-Encoding':'gzip, deflate, br',
        'Connection':'keep-alive'
    }

   
    # for item in deviceList:
    response = requests.post(api_endpoint, json=item)
        # logging.info(f"POST request response for item {item}: {response.text}")

dag = DAG(
    'Danalysis_json_processing_dag',
    default_args=default_args,
    description='DAG to process data from JSON file and make a POST request',
    schedule_interval='@daily',  
)

task_load_data = PythonOperator(
    task_id='load_data_task',
    python_callable=load_data,
    dag=dag,
)

task_extract_data = PythonOperator(
    task_id='extract_data_task',
    python_callable=extract_data,
    provide_context=True,
    dag=dag,
)

task_make_post_request = PythonOperator(
    task_id='make_post_request_task',
    python_callable=make_post_request,
    provide_context=True,
    dag=dag,
)

task_load_data >> task_extract_data >> task_make_post_request

if __name__ == "__main__":
    dag.cli()
