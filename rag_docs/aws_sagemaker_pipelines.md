<!-- source: AWS official documentation (Amazon SageMaker Developer Guide) -->
<!-- title: Amazon SageMaker Pipelines -->
<!-- url: https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html + /pipelines-overview.html -->
<!-- vendor: AWS -->
<!-- topic: ML workflow orchestration, pipeline DAG, step types, data dependencies, drift checks -->

# Amazon SageMaker Pipelines

Amazon SageMaker Pipelines is a purpose-built workflow orchestration service to automate machine learning (ML) development.

Pipelines provide the following advantages over other AWS workflow offerings:

**Auto-scaling serverless infrastructure** You don't need to manage the underlying orchestration infrastructure to run Pipelines. SageMaker automatically provisions, scales, and shuts down the pipeline orchestration compute resources as your ML workload demands.

**Intuitive user experience** Pipelines can be created and managed through a visual editor, SDK, APIs, or JSON. You can drag-and-drop the various ML steps to author your pipelines in the Amazon SageMaker Studio visual interface, or manage workflows programmatically with the SageMaker Python SDK.

**AWS integrations** Pipelines integrate with all SageMaker features and other AWS services to automate data processing, model training, fine-tuning, evaluation, deployment, and monitoring jobs.

**Reduced costs** With Pipelines, you only pay for the SageMaker Studio environment and the underlying jobs that are orchestrated by Pipelines (for example, SageMaker Training, SageMaker Processing, SageMaker Inference, and Amazon S3 data storage).

**Auditability and lineage tracking** You can track the history of pipeline updates and executions using built-in versioning. Amazon SageMaker ML Lineage Tracking helps you analyze the data sources and data consumers in the end-to-end ML development lifecycle.

## Pipelines overview

An Amazon SageMaker pipeline is a series of interconnected steps in a directed acyclic graph (DAG) that are defined using the drag-and-drop UI or the Pipelines SDK. You can also build your pipeline using the pipeline definition JSON schema. This DAG JSON definition gives information on the requirements and relationships between each step of your pipeline.

**The structure of a pipeline's DAG is determined by the data dependencies between steps.** These data dependencies are created when the properties of a step's output are passed as the input to another step.

### Example pipeline DAG

An example DAG includes the following steps:

1. `AbaloneProcess`, an instance of the **Processing** step, runs a preprocessing script on the data used for training (fill in missing values, normalize numerical data, or split data into train, validation, and test datasets).
2. `AbaloneTrain`, an instance of the **Training** step, configures hyperparameters and trains a model from the preprocessed input data.
3. `AbaloneEval`, another **Processing** step, evaluates the model for accuracy. This step shows a data dependency—it uses the test dataset output of `AbaloneProcess`.
4. `AbaloneMSECond` is a **Condition** step which checks that the mean-square-error result of model evaluation is below a certain limit. If the model does not meet the criteria, the pipeline run stops.
5. If the condition passes, the run proceeds:
   - `AbaloneRegisterModel`, a **RegisterModel** step, registers the model as a versioned model package group into the Amazon SageMaker Model Registry.
   - `AbaloneCreateModel`, a **CreateModel** step, creates the model in preparation for batch transform. `AbaloneTransform`, a **Transform** step, generates model predictions on a specified dataset.

### Key Pipelines concepts

- **Pipeline steps / step types**: Processing, Training, Tuning, Model/CreateModel, RegisterModel, Condition, Transform, Callback, and the `@step` decorator to lift-and-shift Python code.
- **Pipeline parameters**: parameterize inputs so the same pipeline definition can be reused across runs.
- **Pass data between steps**: outputs of one step become inputs of another (this forms the DAG).
- **Caching pipeline steps**: skip re-execution of unchanged steps to save time and cost.
- **Retry policy** and **selective execution** of pipeline steps.
- **Drift/quality gates**: baseline calculation, drift detection, and lifecycle with **ClarifyCheck** and **QualityCheck** steps.
- **Scheduling**: schedule pipeline runs (e.g., with EventBridge).
- **Experiments integration** and **local mode** for testing.
