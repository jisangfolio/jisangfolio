<!-- source: Google Cloud official documentation (Vertex AI) -->
<!-- title: Introduction to Vertex AI Pipelines -->
<!-- url: https://cloud.google.com/vertex-ai/docs/pipelines/introduction -->
<!-- vendor: Google Cloud -->
<!-- topic: ML workflow orchestration, KFP/TFX components, ML metadata, artifact lineage -->
<!-- note: extraction cleaned — a garbled product name from auto-extraction ("Agent Platform Pipelines") was corrected to "Vertex AI Pipelines". -->

# Introduction to Vertex AI Pipelines

## Overview

Vertex AI Pipelines is a managed service for orchestrating machine learning (ML) workflows. It lets data scientists and ML engineers automate, monitor, and govern their ML systems in a serverless manner, by running ML workflows as pipelines.

## Core Capabilities

### Workflow automation
Pipelines automate end-to-end ML processes by chaining together discrete steps. Users can build a pipeline and run a pipeline through console interfaces or programmatic APIs, reducing manual intervention in repetitive ML tasks.

### Pipeline components and DSL
Vertex AI Pipelines runs pipelines built with:
- **Kubeflow Pipelines (KFP) SDK** — the primary way to define pipeline components and DAGs.
- **TensorFlow Extended (TFX)** — for pipelines built with the TFX library.
- **Google Cloud Pipeline Components** — pre-built, reusable components for common ML operations.

Users can also build their own custom pipeline components.

### Execution and monitoring
Pipelines support:
- Scheduled runs via the scheduler API
- Event-triggered execution through Pub/Sub integration
- Execution caching to optimize repeated task runs
- Failure policies and retry mechanisms
- Email notifications for run completion and status changes

## ML Metadata and Lineage Tracking

### Vertex ML Metadata
Vertex AI Pipelines automatically records the runs, artifacts, and their relationships using **Vertex ML Metadata**. This captures executions, artifacts, and the connections between datasets, models, and processing steps throughout pipeline runs. Users can track executions and artifacts and define custom schemas to extend the metadata model.

### Artifact lineage
The system tracks the lineage of pipeline artifacts — establishing clear connections between input data, intermediate transformations, and final model outputs. This supports reproducibility and debugging.

## MLOps Integration

Vertex AI Pipelines functions as a core MLOps component by:
- Enabling version control and reuse of workflows through pipeline templates
- Supporting resource labeling for cost allocation and governance
- Letting teams understand pipeline run costs through metadata labels
- Integrating with Vertex AI's broader ML governance tools

## Advanced Features

### Configuration options
- Machine type specification for individual steps
- Private Service Connect interface support for secure execution
- Persistent resource attachment for long-running workflows
- Secret Manager integration for credential handling

### Visualization and templates
- Visualize and analyze pipeline results through dashboards showing the pipeline DAG, step execution times, and artifact dependencies (with HTML/Markdown output for custom reporting)
- A template gallery of pre-built workflows; users can create, upload, and use a pipeline template to standardize processes across teams
