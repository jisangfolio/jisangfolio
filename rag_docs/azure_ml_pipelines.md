<!-- source: Microsoft official documentation (Azure Machine Learning) -->
<!-- title: What are Azure Machine Learning pipelines? -->
<!-- url: https://learn.microsoft.com/en-us/azure/machine-learning/concept-ml-pipelines -->
<!-- vendor: Microsoft Azure -->
<!-- topic: ML pipeline as workflow, MLOps standardization, components, reuse, CI/CD -->

# What are Azure Machine Learning pipelines?

An Azure Machine Learning pipeline is a workflow that automates a complete machine learning task. It standardizes best practices, supports team collaboration, and improves efficiency.

## Why are Azure Machine Learning pipelines needed?

- Standardizes machine learning operations (MLOps) and supports scalable team collaboration
- Improves training efficiency and reduces cost

A pipeline breaks a machine learning task into steps. Each step is a manageable component that can be developed and automated separately. Azure Machine Learning manages dependencies between steps.

### Standardize the MLOps practice and support scalable team collaboration

MLOps automates building and deploying models. Pipelines simplify this process by mapping each step to a specific task, so teams can work independently.

For example, a project may include data collection, preparation, training, evaluation, and deployment. Data engineers, scientists, and ML engineers each own their steps. Steps are best built as components, then integrated into a single workflow. Pipelines can be versioned, automated, and standardized by DevOps practices.

### Training efficiency and cost reduction

Pipelines also improve efficiency and reduce costs. They reuse outputs from unchanged steps and let you run each step on the best compute resource for the task.

## Getting started best practices

You can build a pipeline in several ways, depending on your starting point.

If you are new to pipelines, start by splitting existing code into steps, parameterizing inputs, and wrapping everything into a pipeline.

To scale, use pipeline templates for common problems. Teams fork a template, work on assigned steps, and update only their part as needed.

With reusable pipelines and components, teams can quickly create new workflows by cloning or combining existing pieces.

## Which Azure pipeline technology should I use?

Azure provides several types of pipelines for different purposes:

| Scenario | Primary persona | Azure offering | OSS offering | Canonical pipe | Strengths |
| --- | --- | --- | --- | --- | --- |
| Model orchestration (Machine learning) | Data scientist | Azure Machine Learning Pipelines | Kubeflow Pipelines | Data → Model | Distribution, caching, code-first, reuse |
| Data orchestration (Data prep) | Data engineer | Azure Data Factory pipelines | Apache Airflow | Data → Data | Strongly typed movement, data-centric activities |
| Code & app orchestration (CI/CD) | App Developer / Ops | Azure Pipelines | Jenkins | Code + Model → App/Service | Open/flexible activity support, approval queues, gating |
