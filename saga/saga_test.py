from unittest import TestCase
from unittest.mock import Mock
from . import Saga, Action, SagaError, SagaBuilder


class SagaTest(TestCase):
    def test_run_single_action(self):
        action_call_count = 0

        def action():
            nonlocal action_call_count
            action_call_count += 1
            return None

        action1 = Mock(spec=Action)
        action1.act = action

        (Saga([action1])).execute()

        self.assertEqual(action_call_count, 1)
        self.assertEqual(action1.compensate.call_count, 0)

    def test_run_multiple_actions(self):
        action_call_count = 0
        def action():
            nonlocal action_call_count
            action_call_count += 1
        action1 = Mock(spec=Action)
        action1.act = action
        action2 = Mock(spec=Action)
        action2.act = action
        action3 = Mock(spec=Action)
        action3.act = action
        action4 = Mock(spec=Action)
        action4.act = action

        (Saga([action1, action2, action3, action4])).execute()

        self.assertEqual(action_call_count, 4)
        self.assertEqual(action1.compensate.call_count, 0)
        self.assertEqual(action2.compensate.call_count, 0)
        self.assertEqual(action3.compensate.call_count, 0)
        self.assertEqual(action4.compensate.call_count, 0)

    def test_single_and_only_action_fails(self):
        def ex(**kwargs):
            raise BaseException('test_random_action_of_multiple_fails')
        action = Mock(spec=Action)
        action.act = ex

        with self.assertRaises(BaseException):
            (Saga([action])).execute()

        self.assertEqual(action.compensate.call_count, 1)

    def test_random_action_of_multiple_fails(self):
        action_call_count = 0

        def action():
            nonlocal action_call_count
            action_call_count += 1

        def action_raise(**kwargs):
            raise BaseException('test_random_action_of_multiple_fails')

        action1 = Mock(spec=Action)
        action1.act = action
        action2 = Mock(spec=Action)
        action2.act = action
        action3 = Mock(spec=Action)
        action3.act = action_raise
        action4 = Mock(spec=Action)

        with self.assertRaises(BaseException):
            (Saga([action1, action2, action3, action4])).execute()

        self.assertEqual(action_call_count, 2)
        self.assertEqual(action1.compensate.call_count, 1)
        self.assertEqual(action2.compensate.call_count, 1)
        # can't assert execute as it's not a mock,
        # but then the compensations are triggered by this execute
        self.assertEqual(action3.compensate.call_count, 1)
        self.assertEqual(action4.act.call_count, 0)
        self.assertEqual(action4.compensate.call_count, 0)

    def test_single_compensation_fails(self):
        def ex(**kwargs):
            raise BaseException('test_single_compensation_fails_action')

        def com_ex():
            raise BaseException('test_single_compensation_fails_compensation')

        action = Mock(spec=Action)
        action.act = ex
        action.compensate = com_ex

        with self.assertRaises(SagaError) as context:
            (Saga([action])).execute()

        self.assertIsInstance(context.exception.action, BaseException)
        self.assertEqual(len(context.exception.compensations), 1)
        self.assertIsInstance(context.exception.compensations[0], BaseException)

    def test_raise_original_exception_if_only_one_action_failed(self):
        def action():
            raise ValueError('test_single_compensation_fails_action')
        action1 = Mock(spec=Action)
        action1.act = action

        with self.assertRaises(SagaError):
            (Saga([action1])).execute()

    def test_random_action_of_multiple_fails_and_random_compensation_fails(self):
        action_call_count = 0

        def action():
            nonlocal action_call_count
            action_call_count += 1

        def ex_comp():
            raise BaseException('test_random_action_of_multiple_fails_compensation')

        def ex(**kwargs):
            raise BaseException('test_random_action_of_multiple_fails_action')

        action1 = Mock(spec=Action)
        action1.act = action
        action2 = Mock(spec=Action)
        action2.act = action
        action2.compensate = ex_comp
        action3 = Mock(spec=Action)
        action3.act = ex
        action4 = Mock(spec=Action)

        with self.assertRaises(SagaError) as context:
            (Saga([action1, action2, action3, action4])).execute()

        self.assertEqual(action_call_count, 2)
        self.assertEqual(action1.compensate.call_count, 1)
        self.assertEqual(action3.compensate.call_count, 1)
        self.assertEqual(action4.act.call_count, 0)
        self.assertEqual(action4.compensate.call_count, 0)
        self.assertIsInstance(context.exception.action, BaseException)
        self.assertEqual(len(context.exception.compensations), 1)
        self.assertIsInstance(context.exception.compensations[0], BaseException)

    def test_random_action_of_multiple_fails_and_all_compensations_fail(self):
        action_call_count = 0

        def action():
            nonlocal action_call_count
            action_call_count += 1

        def ex_comp():
            raise BaseException('test_random_action_of_multiple_fails_compensation')

        def action_raises(**kwargs):
            raise BaseException('test_random_action_of_multiple_fails_action')

        action1 = Mock(spec=Action)
        action1.act = action
        action1.compensate = ex_comp
        action2 = Mock(spec=Action)
        action2.act = action
        action2.compensate = ex_comp
        action3 = Mock(spec=Action)
        action3.act = action_raises
        action3.compensate = ex_comp
        action4 = Mock(spec=Action)

        with self.assertRaises(SagaError) as context:
            (Saga([action1, action2, action3, action4])).execute()

        self.assertEqual(action_call_count, 2)
        self.assertEqual(action4.act.call_count, 0)
        self.assertEqual(action4.compensate.call_count, 0)
        self.assertIsInstance(context.exception.action, BaseException)
        self.assertEqual(len(context.exception.compensations), 3)
        self.assertIsInstance(context.exception.compensations[0], BaseException)
        self.assertIsInstance(context.exception.compensations[1], BaseException)
        self.assertIsInstance(context.exception.compensations[2], BaseException)

    def test_action_return_value_is_not_dict(self):
        action = Mock(spec=Action)

        with self.assertRaises(TypeError):
            (Saga([action])).execute()

        self.assertEqual(action.act.call_count, 1)
        self.assertEqual(action.compensate.call_count, 0)


class SagaBuilderTest(TestCase):
    def test_execute_and_compensate(self):
        action_count = 0
        compensation_count = 0

        def action():
            nonlocal action_count
            action_count += 1
            raise BaseException('test_build_saga_action')

        def compensation():
            nonlocal compensation_count
            compensation_count += 1

        with self.assertRaises(BaseException):
            SagaBuilder \
                .create() \
                .action(action, compensation) \
                .build() \
                .execute()
        self.assertEqual(action_count, 1)
        self.assertEqual(compensation_count, 1)

    def test_pass_return_value_to_next_action(self):
        action1_return_value = {'return_value': 'some result'}
        action2_argument = None

        def action1(**kwargs):
            return action1_return_value

        def action2(**kwargs):
            nonlocal action2_argument
            action2_argument = kwargs
            return None

        compensation = Mock()
        saga = SagaBuilder \
            .create() \
            .action(action1, compensation) \
            .action(action2, compensation) \
            .build()
        saga.execute()
        self.assertDictEqual(action1_return_value, action2_argument)

    def test_pass_return_value_to_next_compensation(self):
        action1_return_value = {'return_value': 'some result'}
        compensation2_argument = None

        def action1(**kwargs):
            return action1_return_value

        def action2(**kwargs):
            raise BaseException('fail test action2')

        def compensation2(**kwargs):
            nonlocal compensation2_argument
            compensation2_argument = kwargs

        compensation = Mock()
        try:
            saga = SagaBuilder \
                .create() \
                .action(action1, compensation) \
                .action(action2, compensation2) \
                .build()
            saga.execute()
        except SagaError:
            pass

        self.assertDictEqual(action1_return_value, compensation2_argument)
