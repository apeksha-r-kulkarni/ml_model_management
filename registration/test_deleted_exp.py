import mlflow
from mlflow.tracking import MlflowClient

client = MlflowClient(tracking_uri="http://127.0.0.1:5000")
exp_name = "DeletedExpTest"
exp_id = client.create_experiment(exp_name)
client.delete_experiment(exp_id)

try:
    exp_id_new = client.create_experiment(exp_name)
except Exception as e:
    print("create_experiment failed:", type(e), str(e))
    exp_id_new = client.get_experiment_by_name(exp_name).experiment_id

print("Got exp_id:", exp_id_new)
try:
    with mlflow.start_run(experiment_id=exp_id_new):
        print("Started run!")
except Exception as e:
    print("start_run failed:", type(e), str(e))
