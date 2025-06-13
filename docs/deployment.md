# Deployment

## Testing

GitHub actions are used to automatically run tests with [tox](https://tox.readthedocs.io/en/latest/) and build and deploy the documentation.

Tests are automatically run on any push or pull request to the main branch. More info on the `tox` tests can be seen in the `tox.ini` file, and the GitHub action can be seen in `.github/workflows/test_and_deploy.yml`. Tests are currently only written for model files in the `src/_models` directory. After installing `pytest` and `pytest-cov`, tests can be run locally and code coverage can be seen with `pytest --cov napari_sbem_viewer`.

## Documentation

Documentation is automatically deployed on any push or pull request to the main branch. The GitHub action can be seen in more detail in `.github/workflows/update_docs.yml`. After updating the yaml files in the `docs` directory and pushing the changes, the documentation should be automatically updated in GitHub pages. More information can be seen in the [mkdocs](https://www.mkdocs.org/user-guide/) documentation.

## Pre-commits

The repository contains pre-commits which can be seen in `.pre-commit-config.yaml`. To get started, install `pre-commit` and the necessary `pre-commit` hooks with

    pip install pre-commit
    pre-commit install

Pre-commit checks will then be run when committing new changes to the repo. You can check the pre-commit's are working on the entire codebase with

    pre-commit run --all-files
