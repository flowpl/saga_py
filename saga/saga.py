

class SagaError(BaseException):
    """
    Raised when an action failed and at least one compensation also failed.
    """

    def __init__(self, exception, compensation_exceptions):
        """
        :param exception: BaseException the exception that caused this SagaException
        :param compensation_exceptions: list[BaseException] all exceptions that happened while executing compensations
        """
        self.action = exception
        self.compensations = compensation_exceptions


class Action(object):
    """
    Groups an action with its corresponding compensation. For internal use.
    """
    def __init__(self, action, compensation):
        """

        :param action: Callable a function executed as the action
        :param compensation: Callable a function that reverses the effects of action
        """
        self.__kwargs = None
        self.__action = action
        self.__compensation = compensation

    def act(self, **kwargs):
        """
        Execute this action

        :param kwargs: dict If there was an action executed successfully before this action, then kwargs contains the
                            return values of the previous action
        :return: dict optional return value of this action
        """
        self.__kwargs = kwargs
        return self.__action(**kwargs)

    def compensate(self):
        """
        Execute the compensation.
        :return: None
        """
        if self.__kwargs:
            self.__compensation(**self.__kwargs)
        else:
            self.__compensation()


class Saga(object):
    """
    Executes a series of Actions.
    If one of the actions raises, the compensation for the failed action and for all previous actions
    are executed in reverse order.
    Each action can return a dict, that is then passed as kwargs to the next action.
    While executing compensations possible Exceptions are recorded and raised wrapped in a SagaException once all
    compensations have been executed.
    """
    def __init__(self, actions):
        """
        :param actions: list[Action]
        """
        self.actions = actions

    def execute(self):
        """
        Execute this Saga.
        :return: None
        """
        kwargs = {}
        for action_index in range(len(self.actions)):
            try:
                kwargs = self.__get_action(action_index).act(**kwargs) or {}
            except BaseException as e:
                compensation_exceptions = self.__run_compensations(action_index)
                raise SagaError(e, compensation_exceptions)

            if type(kwargs) is not dict:
                raise TypeError('action return type should be dict or None but is {}'.format(type(kwargs)))

    def __get_action(self, index):
        """
        Returns an action by index.

        :param index: int
        :return: Action
        """
        return self.actions[index]

    def __run_compensations(self, last_action_index):
        """
        :param last_action_index: int
        :return: None
        """
        compensation_exceptions = []
        for compensation_index in range(last_action_index, -1, -1):
            try:
                self.__get_action(compensation_index).compensate()
            except BaseException as ex:
                compensation_exceptions.append(ex)
        return compensation_exceptions


class SagaBuilder(object):
    """
    Build a Saga.
    """
    def __init__(self):
        self.actions = []

    @staticmethod
    def create():
        return SagaBuilder()

    def action(self, action, compensation):
        """
        Add an action and a corresponding compensation.

        :param action: Callable an action to be executed
        :param compensation: Callable an action that reverses the effects of action
        :return: SagaBuilder
        """
        action = Action(action, compensation)
        self.actions.append(action)
        return self

    def build(self):
        """
        Returns a new Saga ready to execute all actions passed to the builder.
        :return: Saga
        """
        return Saga(self.actions)
