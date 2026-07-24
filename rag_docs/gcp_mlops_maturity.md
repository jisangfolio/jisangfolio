<!-- source: Google Cloud Architecture Center -->
<!-- title: MLOps: Continuous Delivery and Automation Pipelines in Machine Learning -->
<!-- url: https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning -->
<!-- vendor: Google Cloud -->
<!-- topic: MLOps maturity levels (0/1/2), pipeline automation, CI/CD, continuous training -->

# MLOps: Continuous Delivery and Automation Pipelines in Machine Learning

## Overview

Machine learning systems require more than just model code to function in production. As illustrated in foundational research, only a small fraction consists of actual ML algorithms—the remainder encompasses configuration, automation, data collection, verification, testing, resource management, model analysis, metadata management, serving infrastructure, and monitoring.

## DevOps versus MLOps

Traditional DevOps emphasizes continuous integration and continuous delivery for software systems. However, ML systems present distinct challenges:

- **Team composition**: Data scientists may lack production software engineering experience
- **Development approach**: ML work is inherently experimental, requiring tracking of various techniques and hyperparameters
- **Testing scope**: Beyond unit and integration tests, ML requires data validation, model quality evaluation, and model validation
- **Deployment complexity**: Rather than deploying a single service, ML requires deploying entire training pipelines capable of automated retraining
- **Production monitoring**: Models degrade through data evolution, not just coding defects

In ML contexts, continuous integration extends to "testing and validating data, data schemas, and models," while continuous delivery encompasses "a system (an ML training pipeline) that should automatically deploy another service." Continuous training (CT) represents a capability unique to ML systems.

## MLOps Level 0: Manual Process

### Characteristics

Level 0 represents the baseline maturity where all steps remain manual:

- **Execution model**: "Every step is manual, including data analysis, data preparation, model training, and validation"
- **Team separation**: Data scientists develop models while separate engineering teams handle deployment, creating potential for training-serving skew
- **Release frequency**: New model versions deploy infrequently—"a couple of times per year"
- **Testing approach**: CI/CD practices are absent; code testing occurs within notebooks or scripts
- **Monitoring gap**: "The process doesn't track or log the model predictions and actions, which are required in order to detect model performance degradation"

### Challenges

This manual approach creates operational vulnerabilities. Models "fail to adapt to changes in the dynamics of the environment, or changes in the data." Organizations must address three key gaps:

1. Active monitoring to detect performance degradation
2. Frequent retraining with recent data to capture emerging patterns
3. Continuous experimentation with new implementations

## MLOps Level 1: ML Pipeline Automation

Level 1 introduces automation of the training pipeline itself, enabling continuous training without manual intervention.

### Core Characteristics

- **Rapid experimentation**: "The steps of the ML experiment are orchestrated. The transition between steps is automated"
- **Continuous training**: "The model is automatically trained in production using fresh data based on live pipeline triggers"
- **Code symmetry**: "The pipeline implementation that is used in the development or experiment environment is used in the preproduction and production environment"
- **Modular architecture**: Components become "reusable, composable, and potentially shareable across ML pipelines," often containerized for environment independence
- **Automated model delivery**: "An ML pipeline in production continuously delivers prediction services to new models"

### Data and Model Validation

Automated validation steps prevent pipeline failures:

**Data validation** checks for:
- Schema skews (unexpected features, missing features, unexpected values)
- Statistical anomalies indicating data pattern changes requiring retraining

**Model validation** comprises:
- Evaluation metrics on test datasets
- Comparison to baseline or production models
- Performance consistency across data segments
- Infrastructure compatibility verification

### Feature Store (Optional)

A centralized feature repository provides multiple benefits:

- Standardizes feature definitions across experiments
- Prevents duplicate or conflicting feature definitions
- Enables "up-to-date feature values from the feature store"
- Crucially, avoids training-serving skew by ensuring identical features for training, experimentation, and online serving

### Metadata Management

Each pipeline execution records:
- Pipeline and component versions executed
- Execution timing and duration
- Parameter configurations
- Artifact locations (prepared data, statistics, validation results)
- Pointers to previous model versions for comparison
- Evaluation metrics enabling performance comparisons

### ML Pipeline Triggers

Automation activates through multiple trigger mechanisms:

- **On-demand**: Manual, ad hoc execution
- **Scheduled**: Systematic retraining (daily, weekly, monthly)
- **Data-driven**: Retraining when new labeled data becomes available
- **Performance-based**: Triggering when metrics degrade
- **Distribution-based**: Response to concept drift indicating data pattern shifts

## MLOps Level 2: CI/CD Pipeline Automation

Level 2 adds CI/CD infrastructure enabling rapid deployment of pipeline changes themselves.

### Pipeline Stages

The complete CI/CD workflow consists of six sequential stages:

1. **Development and experimentation**: Iterative algorithm testing producing ML pipeline source code
2. **Pipeline continuous integration**: Code compilation, component testing, and artifact packaging
3. **Pipeline continuous delivery**: Deploying artifacts to target environments
4. **Automated triggering**: Production pipeline execution based on schedule or trigger conditions
5. **Model continuous delivery**: Serving trained models as prediction services
6. **Monitoring**: Collecting performance statistics on live data, informing subsequent cycles

### Continuous Integration Scope

ML-specific CI testing includes:

- Unit testing feature engineering logic
- Method verification (proper encoding of categorical features)
- Training convergence validation
- Numerical stability checks (preventing NaN outputs)
- Individual component artifact verification
- Inter-component integration testing

### Continuous Delivery Practices

Reliable model delivery requires:

- Infrastructure compatibility verification
- Prediction service API validation
- Performance testing (QPS and latency metrics)
- Data validation for retraining and batch prediction
- Predictive performance target verification
- Progressive deployment (automated testing, semi-automated pre-production, manual production)

## Key Implementation Insights

The document emphasizes that "implementing ML in a production environment doesn't only mean deploying your model as an API for prediction. Rather, it means deploying an ML pipeline that can automate the retraining and deployment of new models."

Organizations need not adopt all maturity levels simultaneously—"You can gradually implement these practices to help improve the automation of your ML system development and production" based on specific operational requirements and data dynamics.
