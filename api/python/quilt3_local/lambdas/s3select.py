from .._upstream import load_module


def lambda_handler(event, context):
    return load_module("lambdas.s3select").lambda_handler(event, context)
