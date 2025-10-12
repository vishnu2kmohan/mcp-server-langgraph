"""
Mutation Testing Configuration for mutmut

Defines which files to mutate and test configuration.
"""


def pre_mutation(context):
    """
    Called before each mutation is tested

    Can be used to skip certain mutations or files
    """
    # Skip test files
    if "test_" in context.filename:
        context.skip = True
        return

    # Skip setup/example files
    skip_files = ["setup.py", "setup_openfga.py", "setup_infisical.py", "example_"]
    if any(skip in context.filename for skip in skip_files):
        context.skip = True
        return

    # Skip __init__.py files (usually just imports)
    if context.filename.endswith("__init__.py"):
        context.skip = True
        return


def post_mutation(context):
    """
    Called after each mutation is tested

    Can be used for custom reporting
    """
    pass
