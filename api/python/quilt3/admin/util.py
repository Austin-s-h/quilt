import typing as T

from .. import _graphql_client
from . import exceptions, types


def unwrap_result(result: T.Any) -> T.Any:
    current = result
    while isinstance(current, _graphql_client.BaseModel):
        fields = tuple(type(current).model_fields)
        if len(fields) != 1:
            return current
        current = getattr(current, fields[0])
    return current


def handle_errors(result: _graphql_client.BaseModel) -> _graphql_client.BaseModel:
    result = unwrap_result(result)
    if isinstance(result, (_graphql_client.InvalidInputSelection, _graphql_client.OperationErrorSelection)):
        raise exceptions.Quilt3AdminError(result)
    return result


def handle_user_mutation(result: _graphql_client.BaseModel) -> types.User:
    return types.User.from_gql(handle_errors(result))


def raise_invalid_input(error: _graphql_client.InvalidInputSelection) -> T.NoReturn:
    first_error = error.errors[0] if error.errors else None
    if first_error is None:
        raise exceptions.InvalidInputError(error)
    if first_error.name == "PolicyDoesNotExist":
        raise exceptions.PolicyNotFoundError()
    if first_error.name == "PolicyTitleConflict":
        raise exceptions.PolicyTitleExistsError(error)
    if first_error.name == "PolicyArnConflict":
        raise exceptions.PolicyArnExistsError(error)
    if first_error.name == "RoleHasTooManyPoliciesToAttach":
        raise exceptions.RoleTooManyPoliciesError(error)
    raise exceptions.InvalidInputError(error)


def raise_operation_error(error: _graphql_client.OperationErrorSelection) -> T.NoReturn:
    raise exceptions.OperationError(error)


def get_client():
    return _graphql_client.Client()
