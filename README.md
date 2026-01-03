# Warranty

This project is meant to explore warranty, and how different aspect of warranty policy are determined.

## Project Summary

This project examines how empirical failure data can be used to inform warranty design decisions from the perspective of a product manufacturer. Using a large, real-world dataset of hard drive operational histories and failure events, the analysis focuses on modelling time-to-failure behaviour and estimating the expected cost of providing warranty coverage over different durations.

A product warranty is treated as a time-limited contract under which the manufacturer bears the cost of replacement if a failure occurs within the coverage period. By analysing observed failure times and appropriately accounting for censored observations where products do not fail within the available data window, the project estimates cumulative failure probabilities and investigates how expected warranty costs evolve as coverage is extended.

The analysis applies core data analytics techniques including data cleaning and validation, exploratory visualisation, and regression-based modelling to identify key drivers of failure risk and to compare risk profiles across hard drive models. These insights are then used to evaluate the trade-off between offering longer warranties and the associated increase in expected cost, highlighting points at which marginal cost grows disproportionately.

The project demonstrates how data-driven analysis can support pricing and product design decisions under uncertainty, reflecting challenges commonly faced in actuarial pricing and risk assessment.

## Key Assumptions

## Data

The dataset is sourced from Backblaze's public hard drive failure data resources, which contains detailed records of hard drive models, their operational status, and failure events over time. The data is available on the follwing [webpage](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data).

## Tools Used to Perform this Analysis

- Python : For data cleaning and initial exploratory analysis
- R : Rest of the project analysis and modelling
- RMarkdown : For generating reports
- GitHub : For version control and project management
- Visual Studio Code : For code editing and development
- Radian : For enhanced R console experience
