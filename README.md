# sync-credentials-aws-to-local
automates the synchronization of AWS credentials from a remote source to local environment files. This ensures seamless authentication across multiple development setups.

## Setup Instructions

1. **Create a `.env` file**:
    - In the root directory of the project, create a file named `.env`.
    - Add your environment-specific variables in this file.

2. **Modify `sync-aws.py` for Initial Setup**:
    - Open the `sync-aws.py` file.
    - Locate the line where `headless=False`.
    - Change `headless=False` to `headless=True` for the initial run to collect credentials.
    - After collecting the credentials, revert the change by setting `headless=True` back to `headless=False`.
    3. **Modify Parameters Before Execution**:
        - Open the `sync-aws.py` file.
        - At the beginning of the file, locate the parameters section.
        - Modify the parameters according to your specific requirements before executing the script.
By following these steps, you ensure that the AWS credentials are properly synchronized and available for your local development environment.